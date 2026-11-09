"""Credential-free checks that the runtime image inputs are pinned (B05)."""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ('@anthropic-ai/claude-code', '@fission-ai/openspec')
VERSION = re.compile(r'\d+\.\d+\.\d+')


def pins(recipe):
    """Return (base reference, {ARG name: default}, installed package specifiers)."""
    lines = recipe.replace('\\\n', ' ').splitlines()
    bases = [line.split()[1] for line in lines if line.startswith('FROM ')]
    if len(bases) != 1:
        raise ValueError('expected exactly one FROM line')
    args = dict(re.findall(r'^ARG ([A-Z_]+)=(\S+)$', recipe, re.MULTILINE))
    installs = []
    for line in lines:
        if 'npm install' in line or 'npm i ' in line:
            for command in line.split('&&'):
                if 'npm install' not in command and 'npm i ' not in command:
                    continue
                for token in command.split():
                    token = token.strip('"\'')
                    if token.startswith('@') or (not token.startswith('-') and '/' not in token
                                                 and token not in ('npm', 'install', 'i')):
                        for name, value in args.items():
                            token = token.replace('${' + name + '}', value).replace('$' + name, value)
                        installs.append(token)
    return bases[0], args, installs


def violations(recipe, tested_cli):
    found = []
    base, args, installs = pins(recipe)
    if not re.fullmatch(r'[a-z0-9./:-]+@sha256:[a-f0-9]{64}', base):
        found.append('base image is not pinned by digest: ' + base)
    seen = {}
    for spec in installs:
        name, _, version = spec.rpartition('@')
        if not name:
            found.append('unpinned package: ' + spec)
            continue
        if not VERSION.fullmatch(version):
            found.append('package is not pinned to an exact version: ' + spec)
        seen[name] = version
    for package in PACKAGES:
        if package not in seen:
            found.append('required package is not installed with a pinned version: ' + package)
    tested = re.match(r'(\d+\.\d+\.\d+)\b', tested_cli)
    cli = seen.get(PACKAGES[0], '')
    if not tested or tested[1] != cli:
        found.append(f'pinned CLI {cli or "(none)"} differs from policy tested.cli {tested_cli!r}')
    return found


class ImagePinTests(unittest.TestCase):
    def setUp(self):
        self.recipe = (ROOT / 'Containerfile').read_text()
        self.tested_cli = json.loads((ROOT / 'agent/policies/default.json').read_text())['tested']['cli']

    def test_shipped_recipe_is_pinned_and_matches_policy(self):
        self.assertEqual(violations(self.recipe, self.tested_cli), [])
        _, args, _ = pins(self.recipe)
        self.assertEqual(args['CLAUDE_CODE_VERSION'], self.tested_cli.split()[0])
        self.assertRegex(self.recipe, r'(?m)^\s+DISABLE_AUTOUPDATER=1$')

    def test_mutated_recipes_are_rejected(self):
        digest = re.search(r'@sha256:[a-f0-9]{64}', self.recipe)
        cases = {
            'tag-only base': self.recipe.replace(digest[0], '') if digest else self.recipe,
            'latest package': self.recipe.replace('"@fission-ai/openspec@${OPENSPEC_VERSION}"',
                                                  '@fission-ai/openspec@latest'),
            'unversioned package': self.recipe.replace('"@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}"',
                                                       '@anthropic-ai/claude-code'),
            'version range': self.recipe.replace('ARG OPENSPEC_VERSION=1.16.0', 'ARG OPENSPEC_VERSION=^1.16.0'),
            'diverging cli': self.recipe.replace('ARG CLAUDE_CODE_VERSION=2.1.316', 'ARG CLAUDE_CODE_VERSION=2.1.317'),
        }
        for name, recipe in cases.items():
            with self.subTest(name=name):
                self.assertNotEqual(recipe, self.recipe)
                self.assertTrue(violations(recipe, self.tested_cli))
        message = violations(cases['diverging cli'], self.tested_cli)
        self.assertTrue(any('2.1.317' in item and '2.1.316' in item for item in message), message)


if __name__ == '__main__':
    unittest.main()
