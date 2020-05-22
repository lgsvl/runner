#!/usr/bin/env python3
#
# Copyright (c) 2020 LG Electronics, Inc.
#
# This software contains code licensed as described in LICENSE.
#

import argparse
import json
import logging
import os
import sys

import lgsvl

FORMAT = '%(asctime)-15s [%(levelname)s][%(module)s] %(message)s'

logging.basicConfig(level=logging.INFO, format=FORMAT)
log = logging.getLogger(__name__)

EGO_TYPE_ID = 1
NPC_TYPE_ID = 2
PEDESTRIAN_TYPE_ID = 3


def load_scene(VSE_dict, sim):
    if "map" not in VSE_dict.keys():
        log.error("No map specified in the scenario")
        sys.exit(1)

    scene = VSE_dict["map"]["name"]
    log.info("Loading {} map".format(scene))
    if sim.current_scene == scene:
        sim.reset()
    else:
        sim.load(scene)


def read_transform(transform_data):
    transform = lgsvl.Transform()
    transform.position = lgsvl.Vector.from_json(transform_data["position"])
    transform.rotation = lgsvl.Vector.from_json(transform_data["rotation"])

    return transform


def read_waypoints(waypoints_data):
    waypoints = []
    for waypoint_data in waypoints_data:
        position = lgsvl.Vector.from_json(waypoint_data["position"])
        speed = waypoint_data["speed"]
        angle = lgsvl.Vector.from_json(waypoint_data["angle"])
        wait_time = waypoint_data["wait_time"]
        waypoint = lgsvl.DriveWaypoint(position, speed, angle=angle, idle=wait_time)
        waypoints.append(waypoint)

    return waypoints


def add_agent(sim, agent_data, agent_type):
    agent_name = agent_data["variant"]
    agent_state = lgsvl.AgentState()
    agent_state.transform = read_transform(agent_data["transform"])

    try:
        if agent_type == lgsvl.AgentType.NPC and "color" in agent_data:
            agent_color = lgsvl.Vector.from_json(agent_data["color"])
            agent = sim.add_agent(agent_name, agent_type, agent_state, agent_color)
        else:
            agent = sim.add_agent(agent_name, agent_type, agent_state)
    except:
        msg = "Agent not found! Please make sure you have a vehicle named "
        msg += "'{}' or have the correct version of simulator".format(agent_name)
        log.error(msg)
        sys.exit(1)

    if agent_type != lgsvl.AgentType.EGO:
        waypoints = read_waypoints(agent_data["waypoints"])
        if waypoints:
            agent.follow(waypoints)

    return agent


def load_agents(VSE_dict, sim):
    if "agents" not in VSE_dict.keys():
        log.warning("No agents specified in the scenario")
        return

    agent_types = {EGO_TYPE_ID: lgsvl.AgentType.EGO,
        NPC_TYPE_ID: lgsvl.AgentType.NPC, PEDESTRIAN_TYPE_ID: lgsvl.AgentType.PEDESTRIAN}
    agents = {type_id: [] for type_id in agent_types}
    agents_data = VSE_dict["agents"]

    for agent_data in agents_data:
        log.debug("Adding agent {}, type: {}".format(agent_data["variant"], agent_data["type"]))
        agent_type_id = agent_data["type"]
        if agent_type_id in agent_types:
            agent = add_agent(sim, agent_data, agent_types[agent_type_id])
            agents[agent_type_id].append(agent)
        else:
            log.warning("Unsupported agent type {}".format(agent_data["type"]))

    log.info("Loaded {} ego agents".format(len(agents[EGO_TYPE_ID])))
    log.info("Loaded {} NPC agents".format(len(agents[NPC_TYPE_ID])))
    log.info("Loaded {} pedestrian agents".format(len(agents[PEDESTRIAN_TYPE_ID])))


def run_vse(json_file, duration=0.0):
    log.debug(f"duration is %s", duration)

    with open(json_file) as f:
        VSE_dict = json.load(f)

    host = os.getenv('SIMULATOR_HOST', "127.0.0.1")
    port = int(os.getenv('SIMULATOR_PORT', 8181))
    log.debug("host is {}, port is {}".format(host, port))
    sim = lgsvl.Simulator(host, port)

    load_scene(VSE_dict, sim)
    load_agents(VSE_dict, sim)

    log.info("Start running scenario...")
    sim.run(duration)
    log.info("Simulation ended")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        log.error("Input file is not specified, please provide json file.")
        sys.exit(1)

    json_file = sys.argv[1]
    run_vse(json_file)
