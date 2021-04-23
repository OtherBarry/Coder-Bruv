from .map import Map
from .player import Player


class GameState:
    """An interface class between Agent/Server and the Players/Map"""

    def set_state(self, state):
        """Sets the games state from JSON"""
        self.tick = state["tick"]
        us_agent = str(state["connection"]["agent_number"])
        them_agent = "0" if us_agent == "1" else "1"
        self.us = Player(state["agent_state"][us_agent])
        self.them = Player(state["agent_state"][them_agent])
        self.agents = {us_agent: self.us, them_agent: self.them}
        self.map = Map(state["world"], state["entities"])
        self.desynced = False

    def update_tick(self, tick):
        """Updates the games current tick"""
        if self.tick == tick - 1:
            self.desynced = False
        else:
            print(
                "ERROR: Desynced. Expected {} | Actual {}".format(self.tick + 1, tick)
            )
            self.desynced = True
        self.tick = tick

    def update_from_event(self, event):
        """Handles an incoming event from the server"""
        event_type = event["type"]
        if event_type == "agent":
            agent_id, action = event["data"]
            self.agents[str(agent_id)].handle_action(action)
        elif event_type == "agent_state":
            data = event["data"]
            self.agents[str(data["number"])].update_state(data)
        elif event_type == "entity_spawned":
            self.map.add_entity(event["data"])
        elif event_type == "entity_expired":
            self.map.remove_entity(tuple(event["data"]))
        elif event_type != "entity_state":
            print("Invalid event type received:", event_type)
