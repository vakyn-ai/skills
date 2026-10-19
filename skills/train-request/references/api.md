# The training-requests API

The request goes to VAKYN through the API, with the person's own key, so it lands on their
organization and they can follow it in the console. Sending is **free**: no balance is needed and
nothing is charged. Template script: [send_request.py](../examples/send_request.py) (standard
library); sample body: [training-request.sample.json](../examples/training-request.sample.json).
Docs: [vakyn.com/docs/training-requests](https://vakyn.com/docs/training-requests).

## Send

`POST https://api.vakyn.com/v1/training-requests` with `Authorization: Bearer vk_...` (the key in
`VAKYN_API_KEY`).

| Field | Rules |
|---|---|
| `schema_version` | `1` (required) |
| `title` | required, up to 200 characters |
| `decision` | required, up to 2,000: what is decided, by whom today, what happens after |
| `runs_on` | `where` (`cloud` or `own_servers`), `region` |
| `model` | the model measured so far (`vakyn-fast`, `vakyn-max`) |
| `questions[]` | 1–20, unique `name`; `type` (`noul`, `choice`, `score`), `instructions`, `options` (object, up to 255), `state` (what the state holds, in words) |
| `examples[]` | up to 50; `input`, `answer`, `question`, and `made_up`, which **must be `true`** |
| `results[]` | up to 100; `question`, `set` (`dev`, `reserved`, `held_out`), `stage` (`before_tuning`, `after_tuning`), `cases`, `right` (≤ `cases`), `metric`, `value`, `source` (the file it came from) |
| `losing_cells[]` | up to 100; `question`, `kind` (`DSP -> CRD`, `false negative`, `too high`, a slice), `count` (≤ `of`), `of`, `note` |
| `needs` | `target`, `volume`, `latency`, `value`, `constraints` (list) |
| `can_share` | `labeled_cases`, `labeled_by`, `terms` (`DPA`, `BAA`, `made-up only`) |
| `contact` | `email` (required), `name`, `company` |
| `proposal_markdown` | the whole `vakyn-proposal.md`, up to 20,000 characters |
| `client` | `skill`, `skills_version` |

**Strict at every level**: an unknown field anywhere is refused. The whole body is at most 128 KB.
`send_request.py check` applies these rules before anything is sent.

## Answers

| Status | Meaning | What to do |
|---|---|---|
| `201` | `{"id": "tr_…", "status": "received", "url": "https://vakyn.com/console/training/tr_…"}` | Give the person the console link |
| `400` | the body is not JSON | A bug in the script |
| `401` | missing, wrong or revoked key | Load `~/.config/vakyn/env`; a new key in the console |
| `403` | the organization is suspended | VAKYN support |
| `413` | over 128 KB | Shorten `proposal_markdown` and the lists |
| `422` | `detail.errors[]`, each with a `path` and a `message` | Fix those fields, show again, ask again |
| `429` | more than 10 requests per organization in 24 hours (`retry-after`) | Wait; do not resend in a loop |
| `404` or no connection | this server has no training-requests API (a self-hosted server, an older one) | Fallback below |

## Follow it

`GET /v1/training-requests` lists the organization's requests, newest first: `id`, `title`,
`status`, `created_at`, `updated_at`, `url`, `quote`. `GET /v1/training-requests/{id}` adds
`messages` (`from`: `vakyn` or `you`) and `request` (the body as stored). `status` is one of
`received`, `reviewing`, `quoted`, `in_training`, `delivered`, `declined`; `quote` is `null` until
`quoted`. `send_request.py status [id]` prints them. Replies appear in the console at
[vakyn.com/console/training](https://vakyn.com/console/training); no email is sent for them.

Before writing a new request, run `status`: the same use case may already be with VAKYN.

## Fallback

No key, a self-hosted server only, or the API is not there: the person pastes `vakyn-proposal.md`
into the [contact form](https://vakyn.com/contact) (topic **Test it on your data**) or emails it.
Same content, no tracking in the console.
