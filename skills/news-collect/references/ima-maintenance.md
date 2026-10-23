# IMA 知识库每日维护操作手册

每日维护 cron (21:00, job_id: `60bbd91f0554`) 的 IMA 相关维护操作。

## 1. 配置

```
KB ID:      ima_kb_e7ouOFmL      # 「AI资讯」，2121+ 条，创建者本人
Config:     ~/.config/ima/ (client_id, api_key)
API Base:   https://ima.qq.com
```

**ID 格式**：IMA 现行 KB ID 是 `ima_kb_xxx` 形式。早期的 base64 串（`AGoC…=`）已失效，继续使用会在 `import_urls` 上返回 `code:220004 invalid knowledge_base_id`。

## 2. 健康检查

### 认证验证

IMA OpenAPI 使用**非标准 header 名**（不是 `X-Client-Id` / `X-Api-Key`）：

```bash
curl -s -X POST "https://ima.qq.com/openapi/wiki/v1/import_urls" \
  -H "Content-Type: application/json" \
  -H "ima-openapi-clientid: $(cat ~/.config/ima/client_id)" \
  -H "ima-openapi-apikey: $(cat ~/.config/ima/api_key)" \
  -d '{"knowledge_base_id":"ima_kb_e7ouOFmL","urls":[]}'
```

| 返回 | 含义 | 处理 |
|------|------|------|
| `code:51` + `Urls: value must contain between 1 and 10 items` | 认证正常（空 urls 是故意的探针） | 无需处理 |
| `code:220004 invalid knowledge_base_id` | 认证正常，**KB ID 过期/不对** | 用下面的 `search_knowledge_base` 重新取 ID |
| `code:200002 skill auth failed` | header 名错误**或**凭证过期 | 先确认 header 名；仍失败就更新 `~/.config/ima/{client_id,api_key}` |
| HTTP 404 | 端点下线 | 查最新文档，别反复重试 |

**220004 与 200002 必须分开看**：前者是「你问的知识库不存在」，后者是「你没通过鉴权」。把 220004 当成凭证问题去换 key，会白折腾。

### 查当前知识库 ID

```bash
curl -s -X POST "https://ima.qq.com/openapi/wiki/v1/search_knowledge_base" \
  -H "Content-Type: application/json" \
  -H "ima-openapi-clientid: $(cat ~/.config/ima/client_id)" \
  -H "ima-openapi-apikey: $(cat ~/.config/ima/api_key)" \
  -d '{"query":"","cursor":"","limit":20}'
```

返回 `data.info_list[]`，每项含 `kb_id` / `kb_name` / `role_type` / `content_count` / `base_type`。`query` 传空串 = 列全部；翻页用 `data.next_cursor`。按 `kb_name` 找「AI资讯」，取 `kb_id`；别按「条目最多的那个」猜。

### 手动补导入（脚本那步失败时）

```bash
curl -s -X POST "https://ima.qq.com/openapi/wiki/v1/import_urls" \
  -H "Content-Type: application/json" \
  -H "ima-openapi-clientid: $(cat ~/.config/ima/client_id)" \
  -H "ima-openapi-apikey: $(cat ~/.config/ima/api_key)" \
  -d '{"knowledge_base_id":"ima_kb_e7ouOFmL","urls":["<URL1>","<URL2>"]}'
```

一次最多 10 个 URL。成功看每个 URL 的 `ret_code: 0`（并返回 `media_id`），不看顶层 `code` 就下结论。

## 3. 已知问题

### 脚本把 IMA 报错淹在日志中段

`collect_v2.py` 只对 `code != 0` 打一行 `⚠️ API 错误`，位置在流程中段；用 `tail` 看结尾常常看不到，而结果 JSON 照样完整输出，容易误报「已入库」。**入库后单独核 IMA 那一行，或直接跑上文的探针**。

### 部分列内容的端点返回 404

`/openapi/wiki/v1/list_by_wiki`、`get_wiki_info` 这类端点会 404（已下线或改名）。列内容改用 `get_knowledge_list`（`{"knowledge_base_id":…,"cursor":"","limit":20}`），列知识库用 `search_knowledge_base`。

## 4. IMA 限制

- 只支持 **URL 导入**，不支持本地文件上传
- 无法解析 X/Twitter 页面（返回 `ret_code 220001`），代码中已自动排除
- 支持来源：公众号、飞书文档、通用网页等公网可访问 URL
