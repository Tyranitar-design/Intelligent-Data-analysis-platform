# Expert Agent Trigger Phrases

## Automatic Routing Rule

Little C should automatically choose the most relevant installed expert when:
- the task clearly matches one expert domain
- the user does not explicitly name another expert
- verification or review is needed after implementation

If the user explicitly names an expert, prioritize that expert's perspective.

## Quick Phrases For The User

### Planning And Scoping

- `小c，先帮我拆这个需求`
- `小c，先把这个想法变成可执行方案`
- `小c，用项目经理视角看一下`

Default routing:
- `project-manager-senior`
- support: `prompt-engineer`, `agents-orchestrator`

### Backend And Data Architecture

- `小c，按后端架构师思路看这个改动`
- `小c，帮我设计这个接口和数据流`
- `小c，看下这个服务边界怎么拆`

Default routing:
- `engineering-backend-architect`
- support: `engineering-security-engineer`, `engineering-code-reviewer`

### Data Pipeline And ETL

- `小c，按数据工程师思路梳理这条管线`
- `小c，帮我设计采集到入库的流程`
- `小c，看下这个 ETL 怎么拆`

Default routing:
- `engineering-data-engineer`
- support: `data-consolidation-agent`, `engineering-backend-architect`

### ML / DL / AI Work

- `小c，用 AI 工程师视角看这个任务`
- `小c，帮我设计这个模型流程`
- `小c，看看这个训练/推理链路`

Default routing:
- `engineering-ai-engineer`
- support: `engineering-data-engineer`, `testing-reality-checker`

### Dashboard And Frontend

- `小c，按前端开发者视角重构这个页面`
- `小c，帮我做这个可视化界面`
- `小c，看下这个交互怎么落地`

Default routing:
- `engineering-frontend-developer`
- support: `engineering-code-reviewer`, `engineering-technical-writer`

### Data Consolidation And Reporting

- `小c，把这些来源的数据整合一下`
- `小c，帮我做成一个统一报表层`
- `小c，按数据整合师思路处理`

Default routing:
- `data-consolidation-agent`
- support: `engineering-data-engineer`, `engineering-technical-writer`

### Security

- `小c，按安全工程师视角过一遍`
- `小c，帮我找下这里的安全风险`
- `小c，看下这块会不会有漏洞`

Default routing:
- `engineering-security-engineer`
- support: `engineering-code-reviewer`, `engineering-backend-architect`

### Code Review

- `小c，按代码审查员模式看一下`
- `小c，帮我做一次严格 review`
- `小c，看看这里有没有回归风险`

Default routing:
- `engineering-code-reviewer`
- support: `engineering-security-engineer`, `testing-reality-checker`

### API Testing And Validation

- `小c，帮我验证这个接口`
- `小c，按测试专家思路验一下`
- `小c，别只看代码，帮我验证结果`

Default routing:
- `testing-api-tester`
- support: `testing-evidence-collector`, `testing-reality-checker`

### Reality Check

- `小c，帮我验证这个说法是不是真的`
- `小c，做一次 reality check`
- `小c，帮我确认这个修复真的生效了`

Default routing:
- `testing-reality-checker`
- support: `testing-evidence-collector`, `testing-api-tester`

### Documentation

- `小c，帮我整理成文档`
- `小c，按技术写作方式输出`
- `小c，把这次改动写成可交接说明`

Default routing:
- `engineering-technical-writer`
- support: `project-manager-senior`, `engineering-backend-architect`

### Multi-Track Coordination

- `小c，这个任务比较复杂，你帮我统筹一下`
- `小c，多个方向一起看`
- `小c，按编排者思路安排一下`

Default routing:
- `agents-orchestrator`
- support: `project-manager-senior`, `prompt-engineer`

