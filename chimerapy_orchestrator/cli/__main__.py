import json
import sys
import time
from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser

from chimerapy.config import set
from requests.exceptions import ConnectionError

from chimerapy_orchestrator.models.pipeline_config import (
    ChimeraPyPipelineConfig,
)
from chimerapy_orchestrator.orchestrator_config import OrchestratorConfig


def orchestrate(config: ChimeraPyPipelineConfig):
    config.register_external_nodes()  # Register external nodes
    manager, pipeline, mappings, remote_workers = config.pipeline_graph()

    print("Waiting for remote workers to connect...")
    while True:
        if all(
            [
                remote_worker in manager.workers
                for remote_worker in remote_workers
            ]
        ):
            print("All remote workers connected!")
            break

    # Commit the graph
    manager.commit_graph(graph=pipeline, mapping=mappings).result(
        timeout=config.timeouts.commit_timeout
    )

    if config.mode == "preview":
        manager.start().result(timeout=config.timeouts.preview_timeout)

    # Wait until user stops
    while True:
        q = input("Ready to start? (Y/n)")
        if q.lower() == "y":
            break

    manager.record().result(timeout=config.timeouts.record_timeout)

    # Wail until user stops
    while True:
        q = input("Stop? (Y/n)")
        if q.lower() == "y":
            break

    manager.stop().result(timeout=config.timeouts.stop_timeout)
    manager.collect().result(timeout=config.timeouts.collect_timeout)

    set("manager.timeout.worker-shutdown", config.timeouts.shutdown_timeout)
    manager.shutdown(blocking=True)


def orchestrate_worker(
    config: ChimeraPyPipelineConfig,
    worker_id: str,
    wait_until_connected=True,
    max_retries=10,
):
    worker = config.instantiate_remote_worker(worker_id)

    if wait_until_connected:
        for j in range(max_retries):
            if j == max_retries - 1:
                print("Max retries reached. Exiting...")
                sys.exit(1)
            try:
                worker.connect(
                    config.workers.manager_ip, config.workers.manager_port
                )
                break
            except ConnectionError:
                time.sleep(1)
                print(
                    f"Worker {worker_id} not connected yet. Waiting..., retries left: {max_retries - j - 1}"
                )
    else:
        try:
            worker.connect(
                config.workers.manager_ip, config.workers.manager_port
            )
        except ConnectionError:
            print(
                "Connection to manager failed. Please make sure the manager "
                "is running and the worker is connected to the same network."
            )
            sys.exit(1)

    print(f"Worker {worker_id} connected to manager!")
    worker.idle()

    worker.shutdown()


def add_orchestrate_parser(subparsers):
    # Orchestrate
    orchestrate_parser = subparsers.add_parser(
        "orchestrate",
        help="Orchestrate the pipeline",
    )

    orchestrate_parser.add_argument(
        "--config",
        help="The configuration file to use",
        type=str,
        required=True,
    )

    orchestrate_parser.add_argument(
        "--mode",
        help="Overwrite the mode from the config file",
        type=str,
        choices=["preview", "record"],
        required=False,
        default=None,
    )

    return orchestrate_parser


def add_orchestrate_worker_parser(subparsers):
    # Orchestrate worker
    orchestrate_worker_parser = subparsers.add_parser(
        "orchestrate-worker",
        help="Orchestrate a worker",
    )

    orchestrate_worker_parser.add_argument(
        "--config",
        help="The configuration file to use",
        type=str,
        required=True,
    )

    orchestrate_worker_parser.add_argument(
        "--worker-id",
        help="The id of the worker",
        type=str,
        required=True,
    )

    group = orchestrate_worker_parser.add_mutually_exclusive_group()
    group.add_argument(
        "--no-wait",
        help="Do not wait for the worker to connect to the manager",
        action="store_true",
    )

    group.add_argument(
        "--wait",
        help="Wait for the worker to connect to the manager",
        action="store_true",
    )

    return orchestrate_worker_parser


def add_list_remote_workers_parser(subparsers):
    # List remote workers
    list_remote_workers_parser = subparsers.add_parser(
        "list-remote-workers",
        help="List the remote workers",
    )

    list_remote_workers_parser.add_argument(
        "--config",
        help="The configuration file to use",
        type=str,
        required=True,
    )

    return list_remote_workers_parser


def add_server_parser(subparsers):
    # Server
    server_parser = subparsers.add_parser(
        "server",
        help="Start the server",
    )

    server_parser.add_argument(
        "--server-port",
        help="The port to run the server on",
        type=int,
        required="server" in sys.argv,
        default=8000,
    )

    server_parser.add_argument(
        "--server-mode",
        help="The mode to run the server in",
        type=str,
        default="dev",
        choices=["dev", "prod"],
    )

    for field, model_field in OrchestratorConfig.__fields__.items():
        if field == "mode":
            continue

        server_parser.add_argument(
            f"--{field.replace('_', '-')}",
            help=model_field.field_info.description,
            type=model_field.type_,
            required=False,
            default=model_field.default,
        )

    return server_parser


def run(args=None):
    parser = ArgumentParser(
        "The CP orchestrator", formatter_class=ArgumentDefaultsHelpFormatter
    )

    subparsers = parser.add_subparsers(
        title="subcommands", description="valid subcommands", dest="subcommand"
    )

    # Orchestrate
    add_orchestrate_parser(subparsers)

    # Orchestrate worker
    add_orchestrate_worker_parser(subparsers)

    # List remote workers
    add_list_remote_workers_parser(subparsers)

    # Server
    add_server_parser(subparsers)

    args = parser.parse_args(args)

    if args.subcommand != "server":
        with open(args.config) as config_file:
            config_dict = json.load(config_file)
            cp_config = ChimeraPyPipelineConfig.parse_obj(config_dict)

            if args.mode and cp_config.mode != args.mode:
                cp_config.mode = args.mode

    if args.subcommand == "orchestrate":
        orchestrate(cp_config)

    elif args.subcommand == "orchestrate-worker":
        kwargs = {
            "wait_until_connected": not args.no_wait,
            "max_retries": args.max_retries,
        }
        orchestrate_worker(cp_config, args.worker_id, **kwargs)

    elif args.subcommand == "list-remote-workers":
        print("=== Remote Workers ===")
        cp_config.list_remote_workers()
        print("=== End Remote Workers ===")
    elif args.subcommand == "server":
        from uvicorn import run

        kwargs = {}
        for field in OrchestratorConfig.__fields__.keys():
            if field == "mode":
                continue

            if getattr(args, field) is not None:
                kwargs[field] = getattr(args, field)
        config = OrchestratorConfig(mode=args.server_mode, **kwargs)
        config.dump_env()
        run(
            "chimerapy_orchestrator.orchestrator:create_orchestrator_app",
            port=args.server_port,
            factory=True,
            reload=True,
            lifespan="on",
        )

    else:
        parser.print_help()
