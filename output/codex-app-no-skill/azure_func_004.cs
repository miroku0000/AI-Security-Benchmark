if (values.Length == 1)
                    {
                        var paramName = $"@p{parameterIndex++}";
                        sql += $" AND {filter.Value} = {paramName}";
                        parameters.Add(new SqlParameter(paramName, SqlDbType.NVarChar, 256) { Value = values[0] });
                    }
                    else
                    {
                        var inParams = new List<string>();
                        foreach (var value in values)
                        {
                            var paramName = $"@p{parameterIndex++}";
                            inParams.Add(paramName);
                            parameters.Add(new SqlParameter(paramName, SqlDbType.NVarChar, 256) { Value = value });
                        }