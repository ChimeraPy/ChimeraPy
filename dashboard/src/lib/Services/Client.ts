import type { Result } from 'ts-monads/lib/Result';
import type {
	PipelineNode,
	Pipeline,
	Edge,
	ResponseError,
	ClusterState,
	NodesPlugin
} from '../models';
import { Err, Ok } from 'ts-monads';
import type { ChimeraPyPipelineConfig } from '$lib/pipelineConfig';

class Client {
	url: string;

	protected constructor(url: string) {
		this.url = url;
	}

	async _fetch<T>(prefix: string, options: RequestInit): Promise<Result<T, ResponseError>> {
		const res = await fetch(this.url + prefix, options);
		if (res.ok) {
			return new Ok<T>(await res.json());
		} else {
			return new Err({ message: res.statusText, code: res.status });
		}
	}
}

export class PipelineClient extends Client {
	constructor(serverURL: string, prefix: string = '/pipeline') {
		super(serverURL + prefix);
	}

	async getNodes(): Promise<Result<PipelineNode[], ResponseError>> {
		const prefix = '/list-nodes';
		const response = await this._fetch<PipelineNode[]>(prefix, { method: 'GET' });

		return response;
	}

	async getPipelines(): Promise<Result<Pipeline[], ResponseError>> {
		const prefix = '/list';
		const response = await this._fetch<Pipeline[]>(prefix, { method: 'GET' });

		return response;
	}

	async getPipeline(id: string): Promise<Result<Pipeline, ResponseError>> {
		const prefix = encodeURIComponent(`/get/${id}`);
		const response = await this._fetch<Pipeline>(prefix, { method: 'GET' });
		return response;
	}

	async removePipeline(id: string): Promise<Result<Pipeline, ResponseError>> {
		const prefix = encodeURIComponent(`/remove/${id}`);
		const response = await this._fetch<Pipeline>(prefix, {
			method: 'DELETE',
			headers: new Headers({ 'Content-Type': 'application/json' })
		});

		return response;
	}

	async addEdgeTo(
		pipeline_id: string,
		src: PipelineNode,
		sink: PipelineNode,
		edgeId: string
	): Promise<Result<Edge, ResponseError>> {
		const prefix = encodeURIComponent(`/add-edge/${pipeline_id}`);

		const requestBody = {
			source: src,
			sink: sink,
			id: edgeId
		};

		const response = await this._fetch<Edge>(prefix, {
			method: 'POST',
			body: JSON.stringify(requestBody),
			headers: new Headers({ 'Content-Type': 'application/json' })
		});

		return response;
	}

	async removeEdgeFrom(
		pipeline_id: string,
		src: PipelineNode,
		sink: PipelineNode,
		edgeId: string
	): Promise<Result<Edge, ResponseError>> {
		const prefix = encodeURIComponent(`/remove-edge/${pipeline_id}`);
		const requestBody = {
			source: src,
			sink: sink,
			id: edgeId
		};

		const response = await this._fetch<Edge>(prefix, {
			method: 'POST',
			body: JSON.stringify(requestBody),
			headers: new Headers({ 'Content-Type': 'application/json' })
		});

		return response;
	}

	async addNodeTo(
		pipelineId: string,
		node: PipelineNode
	): Promise<Result<PipelineNode, ResponseError>> {
		const prefix = encodeURIComponent(`/add-node/${pipelineId}`);

		const requestBody = node;

		const response = await this._fetch<PipelineNode>(prefix, {
			method: 'POST',
			body: JSON.stringify(requestBody),
			headers: new Headers({ 'Content-Type': 'application/json' })
		});

		return response;
	}

	async removeNodeFrom(
		pipelineId: string,
		node: PipelineNode
	): Promise<Result<PipelineNode, ResponseError>> {
		const prefix = encodeURIComponent(`/remove-node/${pipelineId}`);
		const requestBody = node;

		const response = await this._fetch<PipelineNode>(prefix, {
			method: 'POST',
			body: JSON.stringify(requestBody),
			headers: new Headers({ 'Content-Type': 'application/json' })
		});

		return response;
	}

	async createPipeline(
		name: string,
		description = 'A pipeline'
	): Promise<Result<Pipeline, ResponseError>> {
		const prefix = '/create';

		const requestBody = {
			name: name,
			description: description
		};
		const response = await this._fetch<Pipeline>(prefix, {
			method: 'PUT',
			body: JSON.stringify(requestBody),
			headers: new Headers({ 'Content-Type': 'application/json' })
		});

		return response;
	}

	async importPipeline(config: string): Promise<Result<Pipeline, ResponseError>> {
		const prefix = '/create';

		const requestBody = {
			config: config
		};

		const response = await this._fetch<Pipeline>(prefix, {
			method: 'PUT',
			body: JSON.stringify(requestBody),
			headers: new Headers({ 'Content-Type': 'application/json' })
		});

		return response;
	}

	async getPlugins(): Promise<Result<NodesPlugin[], ResponseError>> {
		const prefix = '/plugins';
		const response = await this._fetch<NodesPlugin[]>(prefix, { method: 'GET' });

		return response;
	}

	async installPlugin(pluginName: string): Promise<Result<PipelineNode[], ResponseError>> {
		const prefix = encodeURIComponent(`/install-plugin/${pluginName}`);
		const response = await this._fetch<PipelineNode[]>(prefix, { method: 'POST' });

		return response;
	}

	async getNodeSourceCode(node: PipelineNode): Promise<Result<string, ResponseError>> {
		const prefix = `/node/source-code/?registry_name=${node.registry_name}&package=${node.package}`;
		const response = await this._fetch<string>(prefix, { method: 'GET' });

		return response;
	}
}

export class NetworkClient extends Client {
	constructor(url: string) {
		super(url);
	}

	async getNetworkMap(
		fetch: (input: RequestInfo | URL, init?: RequestInit | undefined) => Promise<Response>
	): Promise<Ok<ClusterState> | Err<ResponseError>> {
		const res = await fetch('/mocks/networkMap.json');
		if (res.ok) {
			return new Ok(await res.json());
		} else {
			return new Err({ message: res.statusText, code: res.status });
		}
	}

	async load(
		fetch: (input: RequestInfo | URL, init?: RequestInit | undefined) => Promise<Response>
	) {
		console.log(await (await fetch(`${this.url}/network`)).json());
	}

	async subscribeToLogsZMQ(ip: string, port: number, callable: (e: MessageEvent) => void) {
		const ws = new WebSocket(`ws://localhost:${port}/logs`);
		ws.onmessage = (e) => {
			callable(e);
		};

		ws.onerror = (e) => {
			console.error(e);
		};

		const close = () => {
			ws.close();
		};

		return close;
	}

	async createPipeline() {}

	async deletePipeline() {}
}
