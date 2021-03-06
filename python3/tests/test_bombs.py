import json
from unittest import TestCase
from unittest.mock import MagicMock, call, patch

from app.state.bombs import Bomb, BombLibrary


def get_generic_entity():
    return {"x": 1, "y": 1, "type": "b", "blast_diameter": 3, "expires": 40, "owner": 0}


def get_generic_bomb():
    return Bomb(get_generic_entity())


class TestBomb(TestCase):
    def test_bomb_constructor_position(self):
        bomb = get_generic_bomb()
        self.assertEqual((1, 1), bomb.position)

    def test_bomb_constructor_radius(self):
        bomb = get_generic_bomb()
        self.assertEqual(1, bomb.radius)

    def test_bomb_constructor_owner(self):
        bomb = get_generic_bomb()
        self.assertEqual("0", bomb.owner)

    def test_bomb_constructor_detonated_by(self):
        bomb = get_generic_bomb()
        self.assertEqual([], bomb.detonates)

    def test_bomb_constructor_detonates(self):
        bomb = get_generic_bomb()
        self.assertEqual([], bomb.detonated_by)

    def test_bomb_constructor_impacts(self):
        bomb = get_generic_bomb()
        self.assertIsNone(bomb.impacts)

    def test_calculate_impacts_no_nodes_in_graph(self):
        map_mock = MagicMock()
        map_mock.graph.__contains__.return_value = False
        bomb = get_generic_bomb()
        bomb.calculate_impacts(map_mock)
        map_mock.graph.__contains__.assert_has_calls(
            [call(i) for i in [(0, 1), (2, 1), (1, 0), (1, 2)]], any_order=True
        )

    def test_calculate_impacts_no_nodes_in_graph_radius_3(self):
        map_mock = MagicMock()
        map_mock.graph.__contains__.return_value = False
        bomb = get_generic_bomb()
        bomb.radius = 3
        bomb.calculate_impacts(map_mock)
        map_mock.graph.__contains__.assert_has_calls(
            [call(i) for i in [(0, 1), (2, 1), (1, 0), (1, 2)]], any_order=True
        )
        self.assertCountEqual([(0, 1), (2, 1), (1, 0), (1, 2)], bomb.impacts)

    def test_calculate_impacts_radius_2(self):
        map_mock = MagicMock()
        map_mock.graph.__contains__.return_value = True
        map_mock.graph.nodes.__getitem__.return_value.get.return_value = None
        bomb = get_generic_bomb()
        bomb.radius = 2
        bomb.calculate_impacts(map_mock)
        coords = [(0, 1), (2, 1), (1, 0), (1, 2), (-1, 1), (3, 1), (1, -1), (1, 3)]
        map_mock.graph.__contains__.assert_has_calls(
            [call(i) for i in coords], any_order=True
        )
        self.assertCountEqual(coords, bomb.impacts)

    def test_calculate_impacts_nodes_called(self):
        map_mock = MagicMock()
        map_mock.graph.__contains__.return_value = True
        map_mock.graph.nodes.__getitem__.__getitem__.return_value = False
        bomb = get_generic_bomb()
        bomb.calculate_impacts(map_mock)
        map_mock.graph.nodes.__getitem__.assert_has_calls(
            [call(i) for i in [(0, 1), (2, 1), (1, 0), (1, 2)]], any_order=True
        )
        map_mock.graph.nodes.__getitem__.return_value.get.assert_has_calls(
            [call("entity") for _ in range(4)], any_order=True
        )
        self.assertCountEqual([(0, 1), (2, 1), (1, 0), (1, 2)], bomb.impacts)

    def test_calculate_impacts_impacts_added(self):
        map_mock = MagicMock()
        map_mock.graph.__contains__.return_value = True
        node_mock = map_mock.graph.nodes.__getitem__.return_value
        node_mock.get.return_value = None
        bomb = get_generic_bomb()
        bomb.calculate_impacts(map_mock)
        self.assertCountEqual([(0, 1), (2, 1), (1, 0), (1, 2)], bomb.impacts)

    def test_bomb_update_tick_early(self):
        bomb = get_generic_bomb()
        bomb.update_tick(2)
        self.assertEqual(bomb.owner, "0")

    def test_bomb_update_tick_one_before(self):
        bomb = get_generic_bomb()
        bomb.update_tick(39)
        self.assertIsNone(bomb.owner)

    def test_bomb_update_tick_on_expire(self):
        bomb = get_generic_bomb()
        bomb.update_tick(40)
        self.assertIsNone(bomb.owner)

    def test_bomb_update_tick_one_after(self):
        bomb = get_generic_bomb()
        bomb.update_tick(41)
        self.assertIsNone(bomb.owner)

    def test_bomb_equal(self):
        bomb = get_generic_bomb()
        other_bomb = get_generic_bomb()
        self.assertEqual(bomb, other_bomb)

    def test_bomb_not_equal(self):
        bomb = get_generic_bomb()
        other_bomb = get_generic_bomb()
        other_bomb.position = (2, 2)
        self.assertNotEqual(bomb, other_bomb)

@patch("app.state.map.Map")
@patch("app.state.bombs.Bomb")
class TestBombLibrary(TestCase):
    def setUp(self):
        self.bl = BombLibrary()

    def test_add_bomb(self, bomb_mock, map_mock):
        entity = {"example": "entity"}
        bomb = bomb_mock.return_value
        bomb.position = (1, 1)
        map = map_mock.return_value
        self.bl.add_bomb(entity, map)
        bomb_mock.assert_called_once_with(entity)
        self.assertIs(bomb, self.bl.get_bomb_at((1, 1)))

    def test_add_two_bombs(self, bomb_mock, map_mock):
        pass

    def test_get_bomb_at(self, bomb_mock, map_mock):
        self.assertIsNone(self.bl.get_bomb_at((1, 1)))
        self.assertIsNone(self.bl.get_bomb_at((2, 2)))
        bomb = bomb_mock.return_value
        bomb.position = (1, 1)
        map = map_mock.return_value
        self.bl.add_bomb({}, map)
        self.assertIs(bomb, self.bl.get_bomb_at((1, 1)))
        self.assertIsNone(self.bl.get_bomb_at((2, 2)))

    def test_update_one_bomb(self, bomb_mock, map_mock):
        bomb = bomb_mock.return_value
        bomb.position = (1, 1)
        bomb.impacts = [(0, 1), (2, 1), (1, 0), (1, 2)]
        bomb.detonates = []
        bomb.detonated_by = []

        map = map_mock.return_value
        self.bl.add_bomb({}, map)
        bomb.calculate_impacts.assert_called_with(map)
        self.bl.update(map)
        bomb.calculate_impacts.assert_called_with(map)
        for coords in bomb.impacts:
            self.assertEqual({bomb, }, self.bl.get_bombs_impacting(coords))

        self.assertEqual([], bomb.detonates)
        self.assertEqual([], bomb.detonated_by)
