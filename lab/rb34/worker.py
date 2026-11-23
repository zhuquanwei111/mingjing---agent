import asyncio
import os
from temporalio.client import Client
from temporalio.worker import Worker
from flow import GovernedRequest, ReceiptNotice
from product import dispatch, reconcile_notice


async def main():
    client = await Client.connect("temporal:7233", namespace=os.environ["NAMESPACE"])
    worker = Worker(client, task_queue="rb34", workflows=[GovernedRequest, ReceiptNotice],
                    activities=[dispatch, reconcile_notice])
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
