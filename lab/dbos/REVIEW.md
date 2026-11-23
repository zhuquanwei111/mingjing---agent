# 独立方案审查与设计处置

事前冻结 aa15c34。独立设计审查 DBOS-SCOPE-PLAN 指出三处假通过风险，均采纳。
* 采用固定 Pydantic AI 2.71.0 的公开 deferred、消息历史和二次 run 接口。核实初次随机 ID、收据、同一 conversation、不同 SDK run。仅复用上游接口及中立收端，DBOS 工作流与产品协议另行实现。
* 固定 DBOS executor_id 与 application_version，死前核未完成对应 step、恢复后同 workflow/同 step 新 PID 与真实引擎重入。新进程只 launch，不调用同名工作流。另改产品读取能力测试老格式。
* 原生对照与受控路径都在工具 202 后、外部效果/费用已提交、步骤未记录处被杀。等第二笔原生费实际提交。要求裸 2/1/2 且扫描阳性。取消在待核仍 PENDING 时进行，产品取消后独立迟到查账。
