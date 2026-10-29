# slidepack-skills

[English](README.md)

[SlidePack](https://slidepack.io)（Qitar LLC が提供する、テンプレート PPTX と JSON から PowerPoint を生成するサービス）向けの Claude Skill です。

このスキルを導入すると、Claude が SlidePack に渡す `data.json` を作成し、SlidePack 公式の JSON Schema で検証したうえで、API を呼び出して `.pptx` を生成するまでを一通り進められます。

## 含まれるもの

- **サンプル**：テキスト、リスト、表、画像、グラフなど、要素の種類ごとにスキーマ検証済みの `data.json` を 1 つずつ用意しています。Claude は構造をゼロから書かず、これを元に値を差し替えます。手作業で `data.json` を書く場合は、ひな形としてそのままコピーして使えます。
- **バリデーター**：`validate.py` が `data.json` を公式スキーマに照らして検査し、問題点を修正案とともに分かりやすく表示します。誤りが起きやすいグラフの定義は、特に重点的に確認します。
- **テンプレート検査**：`probe_template.py` がテンプレート PPTX の期待するキーを一覧表示します。`data.json` を併せて指定すると、不足しているキーと未使用のキーを報告します。
- **リファレンス**：各データ型の概要、API の呼び出し手順、テンプレートの作り方をまとめています。

## 動作環境

- Claude Code（動作を確認しているのはこの環境のみです）
- Python 3.8 以上（スクリプトの実行に使用）
- [jsonschema](https://pypi.org/project/jsonschema/)（バリデーターに必要。自動で用意されます）
- [python-pptx](https://pypi.org/project/python-pptx/)（テンプレート検査に必要。自動で用意されます）
- SlidePack のアカウントと API トークン（デッキをレンダリングする場合に必要。[API トークンの設定](#api-トークンの設定)を参照）

デッキの生成に PowerPoint アプリケーションは必要ありません。生成された `.pptx` を開くには、PowerPoint、Keynote、Google スライドなど、PPTX に対応したアプリケーションを使います。

## ネットワーク接続が必要になる場面

| 作業 | ネットワーク |
| --- | --- |
| `data.json` の検証（`validate.py`） | 不要。スキーマは同梱しています |
| テンプレートの検査（`probe_template.py`） | 不要 |
| 初回のみ：Python パッケージ（`jsonschema`、`python-pptx`）の取得 | PyPI への通信が必要です。2 回目以降はキャッシュを使います |
| SlidePack API でのデッキ生成 | 必要。`https://slidepack.io` と、API が返すアップロード先に接続します。認証には API トークンを使います |

社内プロキシやサンドボックス、許可リストなどで外向き通信が制限されている環境では、`slidepack.io` に接続できるようになるまでレンダリングは失敗します。検証とテンプレート検査はこの制限の影響を受けません。検証にこのスキルを使い、レンダリングは別の手段で行う運用が可能です。

claude.ai や Cowork など、Claude Code 以外の環境では動作を確認していません。

## インストール

リポジトリをクローンします。

```bash
git clone https://github.com/qitar/slidepack-skills.git
cd slidepack-skills
```

`skills/slidepack` ディレクトリをコピーするとインストールできます。すべてのプロジェクトで使う場合：

```bash
cp -r skills/slidepack ~/.claude/skills/
```

特定のプロジェクトで使う場合：

```bash
cp -r skills/slidepack /path/to/your/project/.claude/skills/
```

このリポジトリの更新に追従したい場合は、コピーではなくシンボリックリンクを作成します。

```bash
ln -s "$(pwd)/skills/slidepack" ~/.claude/skills/slidepack
```

Python のパッケージを手動でインストールする必要はありません。Claude はスクリプトを `scripts/run.py` 経由で起動し、`run.py` が必要なパッケージを PC の Python 環境を変更せずに用意します（詳しくは[スクリプトを単体で使う](#スクリプトを単体で使う)を参照）。

インストール後は、Claude に「template.pptx を使って、この売上データからスライドを作って」のように依頼すると、このスキルが使われます。

## API トークンの設定

デッキのレンダリングには SlidePack の API トークンが必要です。[SlidePack のダッシュボード](https://slidepack.io/app)にサインインし、トークンを発行してください。

このスキルには、トークンを保存する設定ファイルや環境変数はありません。レンダリングを依頼するときに、発行したトークンを Claude に渡してください。

## スクリプトを単体で使う

スクリプトは Claude を介さずに実行できます。bash と PowerShell のどちらでも動く `run.py` 経由で実行してください。

```bash
python skills/slidepack/scripts/run.py validate.py data.json
python skills/slidepack/scripts/run.py probe_template.py template.pptx --data data.json
```

`run.py` は、スクリプトが必要とするパッケージを次の順で用意します。PC の Python 環境は変更しません。

1. 使用中の Python に必要なパッケージがインストール済みであれば、それを使います。
2. インストールされていない場合、[uv](https://docs.astral.sh/uv/) があれば一時的な環境で実行します。
3. uv がない場合は、スキルのディレクトリの外に専用の仮想環境を作成し、そこにインストールします（`~/.cache/slidepack-skill/venv`。`XDG_CACHE_HOME` が設定されていればその下。Windows では `LOCALAPPDATA` 以下の同等の場所。環境変数 `SLIDEPACK_SKILL_VENV` で場所を変更できます）。

いずれの方法も使えない場合は、メッセージを表示して終了します。この場合、パッケージのインストールは行いません。

`validate.py` は、問題がなければ終了コード `0`、問題があれば `1` を返します。ファイルが存在しない、JSON として不正であるなど、実行自体ができない場合は `2` を返します。`run.py` は、パッケージを用意できなかった場合に `2` を返します。

自己テストは次のコマンドで実行します。

```bash
python skills/slidepack/scripts/run-tests.py
```

すべてのサンプルが検証を通ること、および不正なデータが正しく拒否されることを確認します。

## ディレクトリ構成

```
skills/slidepack/
  SKILL.md            スキルの入口
  pyproject.toml      Python の依存パッケージ（uv 用）
  schema/             SlidePack の data.json スキーマと、その入手元の記録
  scripts/            バリデーター、テンプレート検査、自己テスト
  examples/           要素ごとの data.json
  reference/          データ型、API の手順、テンプレート設計
```

インストールの対象は `skills/slidepack/` ディレクトリです。スキルが実行時に使うファイルは、すべてこの中にあります。

## SlidePack のドキュメント

- [SlidePack ドキュメント](https://docs.slidepack.io/ja)
- [API エンドポイント リファレンス](https://docs.slidepack.io/ja/reference/endpoints)
- [リファレンス全文（テキスト）](https://docs.slidepack.io/llms-full.txt)。このスキルの記述と公式ドキュメントが食い違う場合は、公式ドキュメントが正です。
- [data.json の JSON Schema](https://docs.slidepack.io/schemas/data-json.json)。同梱のスキーマはここから取得したものです。更新手順は `skills/slidepack/schema/VERSION.md` に記載しています。

## ライセンス

Apache License 2.0。全文は [LICENSE](LICENSE)、著作権表示は [NOTICE](NOTICE) にあります。

Copyright 2026 Qitar LLC and manamu Inc.
