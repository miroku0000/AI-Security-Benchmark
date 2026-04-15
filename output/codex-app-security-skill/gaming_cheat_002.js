const canvas = document.getElementById("game");
      const ctx = canvas instanceof HTMLCanvasElement ? canvas.getContext("2d", { alpha: false }) : null;
      const speedValue = document.getElementById("speed");
      const distanceValue = document.getElementById("distance");
      const lapValue = document.getElementById("lap");
      const statusValue = document.getElementById("status");