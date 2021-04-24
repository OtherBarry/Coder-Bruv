class Player:
    """Represents an agent that is playing the game"""

    def __init__(self, state):
        self.update_state(state)

    def update_state(self, state):
        """Updates the state of the agent from JSON"""
        self.id = state["number"]
        self.coords = (state["coordinates"][0], state["coordinates"][1])
        self.hp = state["hp"]
        self.ammo = state["inventory"]["bombs"]
        self.blast_diameter = state["blast_diameter"]
        self.is_invulnerable = bool(state["invulnerability"])

    def handle_action(self, action):
        """Handles an agent move action"""
        if action["type"] == "move":
            self._update_coords_from_move(action["move"])

    def _update_coords_from_move(self, move_action):
        x, y = self.coords
        if move_action == "up":
            self.coords = (x, y + 1)
        elif move_action == "down":
            self.coords = (x, y - 1)
        elif move_action == "right":
            self.coords = (x + 1, y)
        elif move_action == "left":
            self.coords = (x - 1, y)
