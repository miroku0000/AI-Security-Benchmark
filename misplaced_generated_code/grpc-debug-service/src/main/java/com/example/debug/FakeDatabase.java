package com.example.debug;

import java.sql.SQLException;

public final class FakeDatabase {

  private FakeDatabase() {}

  public static void runQuery(String scenario) throws SQLException {
    if (scenario == null || scenario.isBlank()) {
      SQLException root =
          new SQLException("relation \"users\" does not exist", "42P01", 0);
      SQLException driver =
          new SQLException("Batch entry 0 INSERT INTO users ... was aborted", "23505", 0);
      driver.setNextException(root);
      throw driver;
    }
    if ("timeout".equalsIgnoreCase(scenario)) {
      throw new SQLException("canceling statement due to statement timeout", "57014", 0);
    }
    IllegalStateException inner = new IllegalStateException("connection pool exhausted");
    SQLException sql =
        new SQLException("Failed to acquire connection", "08001", 0, inner);
    throw sql;
  }
}
