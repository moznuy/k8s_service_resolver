import asyncio
import logging
import os

from service_resolver import DNSResolver

TEST_HOST = os.environ['TEST_HOST']
TEST_PROTOCOL = os.environ['TEST_PROTOCOL']
TEST_SVC = os.environ['TEST_SVC']


async def task(r: DNSResolver):
    try:
        print(await r.resolve(TEST_HOST, TEST_PROTOCOL, TEST_SVC))
    except Exception:
        logging.exception('!')
        raise


async def main():
    r = DNSResolver()
    await task(r)
    await task(r)


asyncio.run(main())
