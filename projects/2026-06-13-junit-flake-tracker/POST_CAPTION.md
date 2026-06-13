Built a small JUnit flake tracker today.

It reads JUnit XML reports and points out three things I usually want first in a red pipeline: which tests look flaky, which ones are failing repeatedly, and which ones are just getting too slow.

I kept it standard-library only so it is easy to run against archived CI artifacts locally.
