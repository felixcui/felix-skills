# IMA 知识库每日维护操作手册

每日维护 cron (21:00, job_id: `60bbd91f0554`) 的 IMA 相关维护操作。

## 1. 健康检查

IMA 是腾讯的知识库平台（ima.qq.com），每日采集的文章 URL 会自动导入「AI资讯」知识库。

### 认证验证

IMA OpenAPI 使用**非标准 header 名**（不是 `X-Client-Id` / `X-Api-Key`）：

```bash
curl -s -X POST "https://ima.qq.com/openapi/wiki/v1/import_urls" \
  -H "Content-Type: application/json" \
  -H "ima-openapi-clientid: $(cat ~/.config/ima/client_id)" \
  -H "ima-openapi-apikey: $(cat ~/.config/ima/api_key)" \
  -d '{"knowledge_base_id":"AGoC5oEY8FP12VotR1kff00HlmJyh3RP6Do9vCGKpGQ=","urls":[]}'
```

返回 `code:51`（URL 列表不能为空）= 认证正常。
返回 `code:200002` = header 名错误。
返回 HTTP 404 = 端点不存在或已下线。

### ⚠️ 已知问题：部分 API 端点返回 404

截至 2026-06-02，以下端点返回 HTTP 404（端点可能已下线或路径变更）：

| 端点 | 方法 | 状态 |
|------|------|------|
| `/openapi/wiki/v1/list_by_wiki` | POST | 404 |
| `/openapi/wiki/v1/get_wiki_info` | GET | 404 |

**影响**：无法通过 API 列出 IMA 知识库已有文章，因此维护项 3「IMA 知识库清理」无法自动执行。

**临时替代**：在 IMA 网页端手动检查（ima.qq.com → AI资讯知识库），或依赖 `import_urls` 端点验证认证是否正常。

## 2. 配置

```
KB ID:      AGoC5oEY8FP12VotR1kff00HlmJyh3RP6Do9vCGKpGQ=
Config:     ~/.config/ima/ (client_id, api_key)
API Base:   https://ima.qq.com
```

## 3. IMA 限制

- 只支持 **URL 导入**，不支持本地文件上传
- 无法解析 X/Twitter 页面（返回 ret_code 220001），代码中已自动排除
- 支持来源：公众号、飞书文档、通用网页等公网可访问 URL
