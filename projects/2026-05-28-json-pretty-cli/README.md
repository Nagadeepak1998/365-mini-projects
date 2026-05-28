# JSON Pretty CLI

Small Node.js CLI that reads JSON from a file (or stdin), sorts object keys recursively, and prints pretty-formatted JSON.

## Usage

```bash
node json_pretty.mjs sample-input.json
```

Or with stdin:

```bash
cat sample-input.json | node json_pretty.mjs
```

## Example

Input (`sample-input.json`):

```json
{"z":3,"a":{"d":2,"b":1},"list":[{"y":2,"x":1}]}
```

Output (`sample-output.json`):

```json
{
  "a": {
    "b": 1,
    "d": 2
  },
  "list": [
    {
      "x": 1,
      "y": 2
    }
  ],
  "z": 3
}
```
