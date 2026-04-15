static float compute_control_command(const sensor_data_t *data)
{
    const float temp_setpoint = 27.5f;
    const float pressure_setpoint = 105.0f;
    const float flow_setpoint = 11.0f;