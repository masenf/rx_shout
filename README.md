# repro-datetime-model

This is an example app that is designed to run in "production mode"
with postgres and redis via docker compose.

## How to run

```shell
docker compose build
docker compose up
```

* Access the app on `https://localhost`
* Access postgres via adminer on `http://localhost:8080`
* Access redis store via p3x-redis-ui on `http://localhost:8081`
