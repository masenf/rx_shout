# rx_shout

A shoutbox-like app for posting of images and text. Uses google authentication via
[`reflex-google-auth`](https://github.com/martinxu9/reflex-google-auth).

This is an example app that is designed to run in "production mode"
with postgres and redis via docker compose.

## How to run

(Requires a [Google auth client ID](https://reflex.dev/blog/2023-10-25-implementing-sign-in-with-google/#create-a-google-oauth-client-id);
set via environment var GOOGLE_CLIENT_ID)

```shell
docker compose build
docker compose up
```

* Access the app on `https://localhost`

### How to Embed

If the app is deployed on `https://rx-shout.mooo.com` and the box is being embedded via
a static site generator like jekyll:

```html
<iframe src="https://rx-shout.mooo.com/?topic={{ page.url }}&description={{ page.title }}" style="width: 100%; height: 600px; overflow-x: hidden"></iframe>
```

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

## Backing Up The DB and Uploaded Files

```shell
docker compose exec -it db pg_dump -U postgres > backup.sql
docker compose exec -it app tar cvz /app/uploaded_files > uploaded_files.tar.gz
```

## Restoring the DB and Uploaded Files

```shell
docker compose exec -it db psql -U postgres < backup.sql
docker compose exec -it app tar -C / xvz < uploaded_files.tar.gz
```