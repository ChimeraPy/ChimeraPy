from pathlib import Path
from typing import ClassVar, Dict, List, Tuple

import chimerapy as cp
from pydantic import BaseModel, Field


class ManagerConfig(BaseModel):
    logdir: Path = Field(..., description="The log directory for the manager.")


class WorkerConfig(BaseModel):
    name: str = Field(..., description="The name of the worker.")

    remote: bool = Field(
        default=False,
        description="Indicating the worker is remote and is connected(no creation needed).",
    )


class ChimeraPyPipelineConfig(BaseModel):
    registered_nodes: ClassVar[Dict[str, cp.Node]] = {}

    workers: List[WorkerConfig] = Field(..., description="The workers to be added.")

    nodes: List[str] = Field(..., description="The nodes in the pipeline.")

    adj: List[Tuple[str, str]] = Field(
        ..., description="The edge list of the pipeline graph."
    )

    manager_config: ManagerConfig = Field(..., description="The manager configs.")

    mappings: Dict[str, List[str]] = Field(
        ..., description="The delegation mapping of workers to nodes."
    )

    def manager(self) -> cp.Manager:
        return cp.Manager(**self.manager_config.dict())

    def get_registered_node(self, name) -> cp.Node:
        assert name in self.registered_nodes, f"No node named: {name}"
        NodeClass = self.registered_nodes[name]
        return NodeClass()

    def pipeline_graph(self) -> Tuple[cp.Manager, cp.Graph, Dict[str, List[str]]]:
        created_nodes = {}
        for node_name in self.nodes:
            created_nodes[node_name] = self.get_registered_node(node_name)

        pipeline = cp.Graph()
        pipeline.add_nodes_from(list(created_nodes.values()))
        edges = map(
            lambda edge: (created_nodes[edge[0]], created_nodes[edge[1]]), self.adj
        )
        for edge in edges:
            pipeline.add_edge(*edge)

        workers = []
        for wc in self.workers:
            if not wc.remote:
                wo = cp.Worker(name=wc.name)
                workers.append(wo)

        manager = self.manager()

        list(map(lambda w: w.connect(host=manager.host, port=manager.port), workers))

        mp = {}
        for worker in self.mappings:
            mp[worker] = [
                created_nodes[node_name].name for node_name in self.mappings[worker]
            ]

        return manager, pipeline, mp

    class Config:
        arbitrary_types_allowed = True
