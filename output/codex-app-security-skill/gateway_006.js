const context = createPluginVmContext(name);
  const module = { exports: {} };
  const wrapperSource = `'use strict';\n(function (module, exports) {\n${code.toString("utf8")}\n})`;
  const script = new vm.Script(wrapperSource, {
    filename: `plugin:${name}`,
    displayErrors: false,
  });
  const compiled = script.runInContext(context, { timeout: PLUGIN_TIMEOUT_MS });
  compiled(module, module.exports);
  const exported = module.exports && module.exports.default ? module.exports.default : module.exports;
  return normalizePlugin(name, exported, true);
}