import { writable } from 'svelte/store';
import type { ClusterState, ResponseError } from './models';
import readableWebSocketStore from './Services/ReadableWebSocketStore';

import { networkClient } from './services';

// ToDo: this store is fine for now and distributed async requires the tree to be regenerated in realtime. But something diff based maybe?

export const errorStore = writable<ResponseError | null>(null);
const stores = new Map<string, any>();

export function populateStores() {
	const networkStore = readableWebSocketStore<ClusterState>(
		'/cluster-updates',
		null,
		(data) => data
	);

	stores.set('network', networkStore);
}

export function getStore<T>(name: string): T | null {
	return stores.get(name);
}
