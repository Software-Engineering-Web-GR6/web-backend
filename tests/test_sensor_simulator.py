from sensor_simulator import evolve_environment


class TestSensorSimulator:
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
