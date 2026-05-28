#!/usr/bin/env node

const fs = require('fs');

function readInput(pathArg) {
  if (pathArg) {
    return fs.readFileSync(pathArg, 'utf8');
  }
  return fs.readFileSync(0, 'utf8');
}

function sortKeys(value) {
  if (Array.isArray(value)) {
    return value.map(sortKeys);
  }
  if (value && typeof value === 'object') {
    const out = {};
    for (const key of Object.keys(value).sort()) {
      out[key] = sortKeys(value[key]);
    }
    return out;
  }
  return value;
}

function main() {
  const inputPath = process.argv[2];
  let raw;
  try {
    raw = readInput(inputPath);
  } catch (err) {
    console.error(`Failed to read input: ${err.message}`);
    process.exit(1);
  }

  let parsed;
  try {
    parsed = JSON.parse(raw);
  } catch (err) {
    console.error(`Invalid JSON: ${err.message}`);
    process.exit(1);
  }

  const sorted = sortKeys(parsed);
  process.stdout.write(`${JSON.stringify(sorted, null, 2)}\n`);
}

main();
