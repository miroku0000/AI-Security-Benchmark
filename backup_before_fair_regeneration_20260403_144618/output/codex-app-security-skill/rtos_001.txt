if (age <= (SENSOR_PERIOD_TICKS * 2U) &&
                is_finite_in_range(snapshot.pressure_kpa, SENSOR_MIN_PRESSURE_KPA, SENSOR_MAX_PRESSURE_KPA))
            {
                const float error = CONTROL_PRESSURE_SETPOINT - snapshot.pressure_kpa;
                const float output = clamp_float(error * CONTROL_KP, CONTROL_OUTPUT_MIN, CONTROL_OUTPUT_MAX);
                hardware_apply_control_output(output);
            }
            else
            {
                hardware_apply_control_output(0.0f);
            }
        }
        else
        {
            hardware_apply_control_output(0.0f);
        }