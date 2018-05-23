from sanic import Sanic, response
from sanic_graphql import GraphQLView
from graphql_ws.websockets_lib import WsLibSubscriptionServer
from graphql.execution.executors.asyncio import AsyncioExecutor

import schema
from template import render_graphiql


app = Sanic(__name__)


@app.listener('before_server_start')
def init_graphql(app, loop):
    schema.event_loop = loop
    app.add_route(GraphQLView.as_view(schema=schema.schema,
                                      executor=AsyncioExecutor(loop=loop)),
                                      '/graphql')


@app.route('/graphiql')
async def graphiql_view(request):
    return response.html(render_graphiql())

subscription_server = WsLibSubscriptionServer(schema.schema)


@app.websocket('/subscriptions', subprotocols=['graphql-ws'])
async def subscriptions(request, ws):
    await subscription_server.handle(ws)
    return ws


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4000, debug=True)
