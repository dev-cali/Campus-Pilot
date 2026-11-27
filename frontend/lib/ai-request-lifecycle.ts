export type RequestLease = {
  id: number;
  controller: AbortController;
};

/** Synchronous single-flight gate; cancelled leases can never apply a late response. */
export class AiRequestLifecycle {
  private nextId = 0;
  private active: RequestLease | null = null;

  begin(): RequestLease | null {
    if (this.active) return null;
    const lease = { id: ++this.nextId, controller: new AbortController() };
    this.active = lease;
    return lease;
  }

  isBusy(): boolean {
    return this.active !== null;
  }

  isCurrent(lease: RequestLease): boolean {
    return this.active === lease;
  }

  finish(lease: RequestLease): boolean {
    if (!this.isCurrent(lease)) return false;
    this.active = null;
    return true;
  }

  cancel(): RequestLease | null {
    const lease = this.active;
    if (!lease) return null;
    this.active = null;
    lease.controller.abort();
    return lease;
  }
}
