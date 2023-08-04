# Contributing

Hello! :wave: Thanks for taking the time to contribute.

There are many ways you can contribute :smile:

 - [Pull Request](#pr)
   - 🩹 Submit an obvious fix (e.g. typo)
   - :memo: Work on a bug
 - [Submit an Issue](#issue)
   - :sparkles: Request a feature
   - :bug: Report a bug

Remember to follow the [code of conduct](./CODE_OF_CONDUCT.md)

We use [Poetry](https://python-poetry.org) to manage the project so [make sure you have it](https://python-poetry.org/docs/#installation). Once you do, set up the virtual environment after you cloned repo

```
$ poetry install
```

You can test locally with

```
$ poe test
```

Or (if you don't have [Poe the poet](https://github.com/nat-n/poethepoet))

```
$ poetry run pytest
```

<h2 id="pr">Pull Request contributing guide</h2>

Doing the following will *increase your chances* of your pull request to be accepted :+1:

 - Describe other considered solutions
 - Follow the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) or [Gitmoji](https://gitmoji.dev) commit style
 - For all code-related changes follow the [code style](#cs). Write [tests](#test-guide) if applicable
 - Link to the related issue. If there is none, please [make one](#issue) *or* maybe [the issue is obvious](#minor-pr).

<h3 id="minor-pr">Fixing an obvious issue</h3>

If an issue's solution seems obvious or clear (like fixing a typo or link), you may directly create a PR. Remember to fill in the required forms.

<h3 id="major-pr">Major PR</h3>

If you're making somewhat bigger code changes please write tests if they don't exist already :test_tube:.

If you're fixing a bug :bug:, please remember link to the applicable issue describing the bug like this (if it exists):

```md
 - #issue-number
```

like

```md
 - #42
```

If you're changing/adding documentation, the above isn't required.


### Test guide

When making tests, try to use [Hypothesis](https://hypothesis.works) (if present in `[dev-dependancies]`) for [example data](https://hypothesis.readthedocs.io/en/latest/data.html) as much as possible.

#### Pytest

Please have descriptive test function names. Wrap them in a test class if they serve a similar purpose. There should be more than 1 test class per file. Otherwise, unwrap it from the class and instead put it in the file.

For example, if you have

```py
# test_connection.py

class TestConnection:
    def test_can_con(self): ...
    def test_con_ends_gracefully(self):...
```

And `TestConnection` is the only class in the file, unwrap the tests like so

```py
# test_connection.py

def test_can_con():...
def test_con_ends_gracefully():...
```

#### Ward

If we're using [Ward](https://ward.readthedocs.io/en/latest/), [tags](https://ward.readthedocs.io/en/latest/guide/writing_tests.html#tagging-tests) aren't required but are highly recommended to add.

<h3 id="cs">Code Style</h3>

We use the linters Black, Pylint, and MyPy. We use the formatters Black and Isort.

You can easily fix your code's style with

```
$ poe format
```

or
```
$ shed {{ cookiecutter.module_name }}/**.py
```

You can run the linters via

```
$ poe lint
```

Try to follow [my recommended code style](https://github.com/ThatXliner/Significant-files/blob/main/PYTHON_STYLE.md) or [Google's Style Guide](https://google.github.io/styleguide/pyguide.html)

<h2 id="issue">Creating an issue</h2>

Please remember to fill out all the forms when making an issue :+1:. This includes but is not limited to

 - Describe the issue
 - Reproduction steps
 - System information (e.g. Python version)

Or if it's a feature request :sparkles: (also not limited to)

 - Describe the feature
 - Why the feature cannot exist without changes to code
 - What the new feature might be useful for
