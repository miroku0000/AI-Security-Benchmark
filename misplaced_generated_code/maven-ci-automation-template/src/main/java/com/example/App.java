package com.example;

import generated.antrun.AntrunGenerated;
import generated.exec.ExecGenerated;
import generated.proto.Mark;

public final class App {
  public static void main(String[] args) {
    Mark m = Mark.newBuilder().setId(ExecGenerated.BUILD_ID).build();
    System.out.println(AntrunGenerated.PHASE + " " + m.getId());
  }
}
