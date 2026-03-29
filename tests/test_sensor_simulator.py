from sensor_simulator import evolve_environment, get_device_states


class TestSensorSimulator:
    def test_get_device_states_includes_window_state_and_ac_target_temp(self, monkeypatch):
        class DummyResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return [
                    {"device_type": "fan", "state": "ON"},
                    {"device_type": "air_conditioner", "state": "ON", "target_temp": 22},
                    {"device_type": "air_conditioner", "state": "ON", "target_temp": 24},
                    {"device_type": "light", "state": "OFF"},
                    {"device_type": "window", "state": "OPEN"},
                ]

        def fake_get(*args, **kwargs):
            return DummyResponse()

        monkeypatch.setattr("sensor_simulator.requests.get", fake_get)

        states = get_device_states("token", 1)

        assert states["fan_on"] is True
        assert states["ac_on"] is True
        assert states["light_on"] is False
        assert states["window_open"] is True
        assert states["ac_target_temp"] == 23.0

    def test_ac_target_temp_pulls_room_up_from_20c(self):
        temp, humidity, co2 = 20.0, 54.4, 920.0

        for _ in range(8):
            temp, humidity, co2 = evolve_environment(
                temp=temp,
                humidity=humidity,
                co2=co2,
                states={
                    "fan_on": True,
                    "ac_on": True,
                    "ac_target_temp": 24.0,
                    "window_open": False,
                },
            )

        assert temp > 22.0

    def test_ac_target_temp_stays_near_setpoint(self):
        temp, humidity, co2 = 24.0, 55.0, 900.0

        for _ in range(10):
            temp, humidity, co2 = evolve_environment(
                temp=temp,
                humidity=humidity,
                co2=co2,
                states={
                    "fan_on": True,
                    "ac_on": True,
                    "ac_target_temp": 24.0,
                    "window_open": False,
                },
            )

        assert 23.0 <= temp <= 25.0
