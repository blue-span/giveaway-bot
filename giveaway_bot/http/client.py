from contextlib import asynccontextmanager, AsyncExitStack

import trio
import ssl
import h11


def tls_context():
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = True
    ssl_context.verify_mode = ssl.CERT_REQUIRED
    return ssl_context



async def tls_connect(server_hostname,
	              tcp_port):
    tcp_stream = await trio.open_tcp_stream(server_hostname, tcp_port)
    ssl_context = tls_context()
    tls_stream = trio.SSLStream(
        transport_stream=tcp_stream,
	ssl_context=ssl_context,
	server_hostname=server_hostname,
	https_compatible=True
    )

    await tls_stream.do_handshake()

    return tls_stream


async def tls_teardown(stream):
    await stream.aclose()


max_recv = 32 * 1024


@asynccontextmanager
async def factory(hostname, port):
    async with AsyncExitStack() as stack:
        async def connect():
            stream = await tls_connect(hostname, port)
            async def teardown():
                return await tls_teardown(stream)
            stack.push_async_callback(teardown)
            return stream

        async def send_events(connection, stream, events):
            for event in events:
                data = connection.send(event)
                await stream.send_all(data)
            if not isinstance(event, h11.EndOfMessage):
                data = connection.send(h11.EndOfMessage())
                await stream.send_all(data)

        async def collect_events(connection, stream):
            while True:
                event = connection.next_event()
                if event is h11.NEED_DATA:
                    data = await stream.receive_some(max_recv)
                    connection.receive_data(data)
                elif type(event) is h11.EndOfMessage:
                    return
                else:
                    yield event

        stream = await connect()
        connection = h11.Connection(our_role=h11.CLIENT)

        async def make_request(*events):
            nonlocal stream, connection
            if connection.our_state in {h11.MUST_CLOSE, h11.CLOSED}:
                await stack.aclose()
                stream = await connect()
                connection = h11.Connection(our_role=h11.CLIENT)
            if connection.states == {h11.CLIENT: h11.DONE, h11.SERVER: h11.DONE}:
                connection.start_next_cycle()

            await send_events(connection, stream, events)
            async for event in collect_events(connection, stream):
                yield event


        yield make_request
