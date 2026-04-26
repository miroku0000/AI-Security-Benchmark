import { createForwardRequest, getCorsHeaders, addCorsHeaders } from "./handlers/request-forwarding.js";
import { handleError, handleCorsPreFlight } from "./handlers/error-handler.js";
import { getConfig } from "./config.js";

export default {
  async fetch(request, env, ctx) {
    const config = getConfig(env);
    const corsHeaders = getCorsHeaders();

    if (request.method === "OPTIONS") {
      return handleCorsPreFlight(corsHeaders);
    }

    try {
      const url = new URL(request.url);
      const backendUrl = new URL(
        url.pathname + url.search,
        config.backendUrl
      );

      const forwardRequest = createForwardRequest(request, backendUrl.toString());
      const response = await fetch(forwardRequest);

      return addCorsHeaders(response, corsHeaders);
    } catch (error) {
      return handleError(error, corsHeaders);
    }
  },
};