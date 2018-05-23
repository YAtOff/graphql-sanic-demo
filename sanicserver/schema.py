"""
type Channel {
  id: ID!
  name: String
  messages: [Message]!
}

type Message {
  id: ID!
  text: String
}

# This type specifies the entry points into our API
type Query {
  channels: [Channel]
  channel(id: ID!): Channel
}

input MessageInput{
  channelId: ID!
  text: String
}

# The mutation root type, used to define all mutations
type Mutation {
  addChannel(name: String!): Channel
  addMessage(message: MessageInput!): Message
}

type Subscription {
  messageAdded(channelId: ID!): Message
}
"""

import asyncio
import graphene


event_loop = None
queues = {}


def queue_of(channel_id):
    channel_id = str(channel_id)
    if channel_id not in queues:
        assert event_loop is not None
        queues[channel_id] = asyncio.Queue(loop=event_loop)
    return queues[channel_id]


next_id = {
    'channel': 0,
    'message': 0
}

def make_id(type):
    next_id[type] += 1
    return next_id[type]


class Message(graphene.ObjectType):
    id = graphene.ID()
    text = graphene.String()


class Channel(graphene.ObjectType):
    id = graphene.ID()
    name = graphene.String()
    messages = graphene.List(Message)


channels = [
    Channel(id=make_id('channel'), name='soccer', messages=[]),
    Channel(id=make_id('channel'), name='baseball', messages=[])
]


class Query(graphene.ObjectType):
    channels = graphene.List(Channel)
    channel = graphene.Field(Channel, id=graphene.ID())

    def resolve_channels(self, info):
        return channels

    def resolve_channel(self, info, id):
        return next((c for c in channels if str(c.id) == id), None)


class AddChannel(graphene.Mutation):

    class Arguments:
        name = graphene.String()

    id = graphene.ID()
    name = graphene.String()

    def mutate(self, info, name):
        channel = Channel(id=make_id('channel'), name=name, messages=[])
        channels.append(channel)
        return AddChannel(id=channel.id, name=channel.name)


class MessageInput(graphene.InputObjectType):
    channel_id = graphene.ID()
    text = graphene.String()


class AddMessage(graphene.Mutation):
    class Arguments:
        message = MessageInput(required=True)

    id = graphene.ID()
    text = graphene.String()

    async def mutate(self, info, message):
        channel = next((c for c in channels if str(c.id) == message.channel_id), None)
        if channel:
            msg = Message(id=make_id('message'), text=message.text)
            channel.messages.append(msg)
            print(f'publish -> channel: {channel}, message: -> {message}')
            await queue_of(channel.id).put(msg)
            return AddMessage(id=msg.id, text=msg.text)


class Mutations(graphene.ObjectType):
    add_channel = AddChannel.Field()
    add_message = AddMessage.Field()


class Subscription(graphene.ObjectType):
    """
    type Subscription {
      messageAdded(channelId: ID!): Message
    }
    """
    message_added = graphene.Field(Message, channel_id=graphene.ID())

    async def resolve_message_added(self, info, channel_id):
        print(f'subscription -> info: {info}, channel_id: -> {channel_id}')
        queue = queue_of(channel_id)
        while True:
            message = await queue.get()
            print(f'got message -> channel id: {channel_id}, message: -> {message}')
            yield message


schema = graphene.Schema(query=Query, mutation=Mutations, subscription=Subscription)
