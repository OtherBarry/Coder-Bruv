import json
from unittest import TestCase
from unittest.mock import call, patch

from app.state.map import Map


def generate_empty_map():
    return Map({"width": 9, "height": 9}, [])


class TestMap(TestCase):
    def test_init_empty_map_size(self):
        map = generate_empty_map()
        self.assertEqual(9 * 9, len(map.graph.nodes))

    def test_init_empty_map_weight(self):
        map = generate_empty_map()
        for node in map.graph.nodes:
            self.assertEqual(100, map.graph.nodes[node]["weight"])

    @patch("app.state.map.Map.add_entity", autospec=True)
    def test_init_default_map_entities(self, mocked):
        with open("tests/data/default_state.json") as f:
            state = json.load(f)
        map = Map(state["world"], state["entities"])
        mocked.assert_has_calls(
            [call(map, e) for e in state["entities"]], any_order=True
        )

    def test_add_entity_ammo(self):
        map = generate_empty_map()
        map.add_entity({"x": 0, "y": 0, "type": "a", "expires": 40})
        self.assertEqual("a", map.graph.nodes[(0, 0)]["entity"])
        self.assertEqual(100 + Map.WEIGHT_MAP["a"], map.graph.nodes[(0, 0)]["weight"])

    def test_add_entity_bomb_1(self):
        map = generate_empty_map()
        map.add_entity(
            {
                "x": 1,
                "y": 1,
                "type": "b",
                "blast_diameter": 3,
                "expires": 40,
                "owner": 0,
            }
        )
        map.bomb_library.update(map)
        self.assertNotIn((1, 1), map.graph)
        impacted_nodes = ((0, 1), (2, 1), (1, 0), (1, 2))
        for node in map.graph.nodes:
            if node in impacted_nodes:
                self.assertEqual(
                    100 + Map.WEIGHT_MAP["Future Blast Zone"], map.graph.nodes[node]["weight"]
                )
            else:
                self.assertEqual(100, map.graph.nodes[node]["weight"])

    def test_add_entity_bomb_2(self):
        map = generate_empty_map()
        map.add_entity(
            {
                "x": 2,
                "y": 2,
                "type": "b",
                "blast_diameter": 5,
                "expires": 40,
                "owner": 0,
            }
        )
        map.bomb_library.update(map)
        self.assertNotIn((2, 2), map.graph)
        impacted_nodes = (
            (0, 2),
            (1, 2),
            (3, 2),
            (4, 2),
            (2, 0),
            (2, 1),
            (2, 3),
            (2, 4),
        )
        for node in map.graph.nodes:
            if node in impacted_nodes:
                self.assertEqual(
                    100 + Map.WEIGHT_MAP["Future Blast Zone"], map.graph.nodes[node]["weight"]
                )
            else:
                self.assertEqual(100, map.graph.nodes[node]["weight"])

    def test_add_entity_powerup(self):
        map = generate_empty_map()
        map.add_entity({"x": 3, "y": 3, "type": "bp", "expires": 40})
        self.assertEqual("bp", map.graph.nodes[(3, 3)]["entity"])
        self.assertEqual(100 + Map.WEIGHT_MAP["bp"], map.graph.nodes[(3, 3)]["weight"])

    def test_add_entity_metal(self):
        map = generate_empty_map()
        map.add_entity({"x": 4, "y": 4, "type": "m"})
        self.assertNotIn((4, 4), map.graph)

    def test_add_entity_ore(self):
        map = generate_empty_map()
        map.add_entity({"x": 5, "y": 5, "type": "o", "hp": 3})
        self.assertNotIn((5, 5), map.graph)

    def test_add_entity_fire(self):
        pass

    def test_add_entity_wood(self):
        map = generate_empty_map()
        map.add_entity({"x": 6, "y": 6, "type": "w", "hp": 1})
        self.assertNotIn((6, 6), map.graph)

    def test_add_entity_blast(self):
        map = generate_empty_map()
        map.add_entity({"x": 2, "y": 2, "type": "x", "expires": 10})
        self.assertEqual("x", map.graph.nodes[(2, 2)]["entity"])
        self.assertEqual(100 + Map.WEIGHT_MAP["x"], map.graph.nodes[(2, 2)]["weight"])

    def test_remove_entity_ammo(self):
        map = generate_empty_map()
        map.add_entity({"x": 0, "y": 0, "type": "a", "expires": 40})
        map.remove_entity((0, 0))
        self.assertEqual(100, map.graph.nodes[(0, 0)]["weight"])

    def test_remove_entity_bomb(self):
        map = generate_empty_map()
        map.add_entity(
            {
                "x": 2,
                "y": 2,
                "type": "b",
                "blast_diameter": 5,
                "expires": 40,
                "owner": 0,
            }
        )
        map.bomb_library.update(map)
        map.remove_entity((2, 2))
        map.bomb_library.update(map)
        for node in map.graph.nodes:
            self.assertEqual(100, map.graph.nodes[node]["weight"])

    def test_remove_entity_powerup(self):
        map = generate_empty_map()
        map.add_entity({"x": 3, "y": 3, "type": "bp", "expires": 40})
        map.remove_entity((3, 3))
        self.assertEqual(100, map.graph.nodes[(3, 3)]["weight"])

    def test_remove_entity_metal(self):
        map = generate_empty_map()
        map.add_entity({"x": 4, "y": 4, "type": "m"})
        map.remove_entity((4, 4))
        self.assertEqual(100, map.graph.nodes[(4, 4)]["weight"])

    def test_remove_entity_ore(self):
        map = generate_empty_map()
        map.add_entity({"x": 5, "y": 5, "type": "o", "hp": 3})
        map.remove_entity((5, 5))
        self.assertEqual(100, map.graph.nodes[(5, 5)]["weight"])

    def test_remove_entity_fire(self):
        pass

    def test_remove_entity_wood(self):
        map = generate_empty_map()
        map.add_entity({"x": 6, "y": 6, "type": "w", "hp": 1})
        map.remove_entity((6, 6))
        self.assertEqual(100, map.graph.nodes[(6, 6)]["weight"])

    def test_remove_entity_blast(self):
        map = generate_empty_map()
        map.add_entity({"x": 2, "y": 2, "type": "x", "expires": 10})
        map.remove_entity((2, 2))
        self.assertEqual(100, map.graph.nodes[(2, 2)]["weight"])
