"""Utilities for creating ZeroMQ sockets used across services."""

from __future__ import annotations

import zmq

TOPIC_EVENTS = "events"
TOPIC_HEALTH = "health"


def make_req(ctx: zmq.Context, address: str) -> zmq.Socket:
    """Create a REQ socket connected to the given address."""

    socket = ctx.socket(zmq.REQ)
    socket.connect(address)
    return socket


def make_rep(ctx: zmq.Context, address: str) -> zmq.Socket:
    """Create a REP socket bound to the given address."""

    socket = ctx.socket(zmq.REP)
    socket.bind(address)
    return socket


def make_pub(ctx: zmq.Context, address: str, *, bind: bool = True) -> zmq.Socket:
    """Create a PUB socket for the given address."""

    socket = ctx.socket(zmq.PUB)
    if bind:
        socket.bind(address)
    else:
        socket.connect(address)
    return socket


def make_sub(
    ctx: zmq.Context,
    address: str,
    topics: list[str] | None = None,
    *,
    bind: bool = False,
) -> zmq.Socket:
    """Create a SUB socket for the given address and subscribe to topics."""

    socket = ctx.socket(zmq.SUB)
    if bind:
        socket.bind(address)
    else:
        socket.connect(address)
    if not topics:
        socket.setsockopt_string(zmq.SUBSCRIBE, "")
    else:
        for topic in topics:
            socket.setsockopt_string(zmq.SUBSCRIBE, topic)
    return socket

