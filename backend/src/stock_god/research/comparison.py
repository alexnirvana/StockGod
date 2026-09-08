from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import select
from stock_god.db.models import Job
from stock_god.db.session import owner
from stock_god.trading.engine import money


def compare(session, identifiers):
    if not 2 <= len(identifiers) <= 3 or len(set(identifiers)) != len(identifiers):
        raise HTTPException(422, '请选择两到三个不同的已完成实验。')
    found = {j.id: j for j in session.scalars(select(Job).where(Job.player_id == owner(session), Job.id.in_(identifiers)))}
    if len(found) != len(identifiers):
        raise HTTPException(404, '部分实验不存在于当前账号。')
    jobs = [found[identifier] for identifier in identifiers]
    if any(j.status != 'completed' or not j.result for j in jobs):
        raise HTTPException(409, '请等待所选实验全部完成后再比较。')
    versions = {(j.result['data_version'], j.result['rule_version'], j.result['strategy_version'], j.result['matching']) for j in jobs}
    if len(versions) != 1:
        raise HTTPException(409, '数据、规则、策略或成交模型版本不同，不能直接比较。')
    indexes = [{point['day']: point for point in j.result['curve']} for j in jobs]
    days = sorted(set.intersection(*(set(index) for index in indexes)))
    if len(days) < 2:
        raise HTTPException(409, '所选实验没有足够的共同区间。')
    rows = []
    for job, index in zip(jobs, indexes):
        base = Decimal(index[days[0]]['equity'])
        if base <= 0:
            raise HTTPException(409, '实验净值无法用于归一化比较。')
        peak, worst = Decimal(100), Decimal(0)
        curve = []
        for day in days:
            normalized = Decimal(index[day]['equity']) / base * 100
            peak = max(peak, normalized)
            worst = max(worst, (1 - normalized / peak) * 100)
            curve.append({'day': day, 'value': str(money(normalized))})
        rows.append({'id': job.id, 'params': job.params, 'curve': curve,
                     'common_return': str(money(Decimal(index[days[-1]]['equity']) / base * 100 - 100)),
                     'common_drawdown': str(money(worst)),
                     'original_return': job.result['total_return'], 'original_fees': job.result['fees'],
                     'original_trade_count': job.result['trade_count']})
    return {'start_day': days[0], 'end_day': days[-1], 'data_version': jobs[0].result['data_version'], 'rows': rows,
            'notes': ['共同区间以第一天收盘净值归一为 100，收益与回撤从该时点开始计算，包含原有持仓的后续表现。',
                      '原始报告收益、总费用和成交数仍按各自完整运行区间展示，不与共同区间指标混用。',
                      '相同数据上反复挑选最高收益参数可能过拟合，比较结果不能证明未来收益。']}
