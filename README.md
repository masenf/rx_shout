# repro-datetime-model

This is an example app that is designed to run in "production mode"
with postgres and redis via docker compose.

## How to run

```shell
docker compose build
docker compose up
```

* Access the app on `https://localhost`

## Run With Prod Services

```shell
docker compose -f compose.yaml -f compose.prod.yaml up -d
```

* Access the app on `https://localhost`

## Run With Admin Tools

```shell
docker compose -f compose.yaml -f compose.prod.yaml -f compose.tools.yaml up
```

* Access postgres via adminer on `http://localhost:8080`
* Access redis store via p3x-redis-ui on `http://localhost:8081`

Based on the example at [reflex/reflex-dev](https://github.com/reflex-dev/reflex/tree/main/docker-example)
