source.push(`double ${prefix}_value = params.${prefix}_missing;`);
  source.push(`if (doc.containsKey(${JSON.stringify(field)}) && doc[${JSON.stringify(field)}].size() != 0) { ${prefix}_value = doc[${JSON.stringify(field)}].value; }`);
  source.push(`if (${prefix}_value < params.${prefix}_min) { ${prefix}_value = params.${prefix}_min; }`);
  source.push(`if (${prefix}_value > params.${prefix}_max) { ${prefix}_value = params.${prefix}_max; }`);
  source.push(`double ${prefix}_contribution = ${prefix}_value;`);
  source.push(`if (params.${prefix}_modifier == 'log1p') { ${prefix}_contribution = Math.log(1 + Math.max(0.0, ${prefix}_value)); }`);
  source.push(`else if (params.${prefix}_modifier == 'sqrt') { ${prefix}_contribution = Math.sqrt(Math.max(0.0, ${prefix}_value)); }`);
  source.push(`else if (params.${prefix}_modifier == 'reciprocal') { ${prefix}_contribution = 1.0 / (1.0 + Math.abs(${prefix}_value)); }`);
  source.push(`${prefix}_contribution = ${prefix}_contribution * params.${prefix}_factor * params.${prefix}_weight;`);