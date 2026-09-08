import { t, useLocale } from '../i18n'
import { useEffect, useRef } from 'react';
import * as echarts from 'echarts/core';
import { CandlestickChart, BarChart, LineChart } from 'echarts/charts';
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import type { Bar, Job } from '../lib/types';
import type { ComparisonReport } from '../features/experiments/Comparison';
echarts.use([CandlestickChart, BarChart, LineChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer]);
export function ComparisonChart({ report }: { report: ComparisonReport }) {
    const locale = useLocale();
    const ref = useRef<HTMLDivElement>(null);
    useEffect(() => {
        if (!ref.current) return;
        const chart = echarts.init(ref.current);
        chart.setOption({ animation: false, color: ['#7990ff', '#31d6c6', '#ffba69'],
            tooltip: { trigger: 'axis' }, legend: { top: 0, textStyle: { color: '#99abcd' } },
            grid: { top: 42, right: 20, left: 48, bottom: 30 },
            xAxis: { type: 'category', data: report.rows[0].curve.map(p => 'D' + (p.day + 1)), axisLabel: { color: '#99abcd' } },
            yAxis: { type: 'value', scale: true, axisLabel: { color: '#99abcd' }, splitLine: { lineStyle: { color: '#192536' } } },
            series: report.rows.map(row => ({ type: 'line', showSymbol: false,
                name: `MA ${row.params.short_window}/${row.params.long_window} · ${row.params.allocation}% · ${row.id.slice(0, 6)}`,
                data: row.curve.map(p => Number(p.value)) })) });
        const resize = new ResizeObserver(() => chart.resize());
        resize.observe(ref.current);
        return () => { resize.disconnect(); chart.dispose(); };
    }, [report, locale]);
    return <div ref={ref} className="comparison-chart" role="img" aria-label={t('共同区间归一化净值比较图，数值见下表')}/>;
}
export function aggregateBars(bars: Bar[], size: number): Bar[] {
    const groups: Bar[] = [];
    for (let i = 0; i < bars.length; i += size) {
        const b = bars.slice(i, i + size);
        groups.push({ day: b[b.length - 1].day, open: b[0].open, close: b[b.length - 1].close,
            high: String(Math.max(...b.map(x => Number(x.high)))), low: String(Math.min(...b.map(x => Number(x.low)))),
            volume: b.reduce((sum, x) => sum + x.volume, 0), suspended: b.every(x => x.suspended) });
    }
    return groups;
}
export function Chart({ bars, period = 1, compact = false, report }: {
    bars?: Bar[];
    period?: number;
    compact?: boolean;
    report?: Job['result'];
}) {
    const locale = useLocale();
    const ref = useRef<HTMLDivElement>(null);
    useEffect(() => {
        if (!ref.current)
            return;
        const chart = echarts.init(ref.current);
        const rows = aggregateBars(bars || [], period);
        const common = { animation: false, textStyle: { color: '#8c9db9', fontFamily: 'system-ui' }, backgroundColor: 'transparent',
            tooltip: { trigger: 'axis', backgroundColor: '#101c2e', borderColor: '#2c4267', textStyle: { color: '#eaf0ff' } },
            grid: { top: 15, right: 44, left: compact ? 5 : 46, bottom: 30 },
            xAxis: { type: 'category', data: report ? report.curve.map(x => t("第") + (x.day + 1) + t("日")) : rows.map(x => 'D' + (x.day + 1)), axisLine: { lineStyle: { color: '#2c374a' } }, axisTick: { show: false } },
            yAxis: { type: 'value', scale: true, position: compact ? 'right' : 'left', splitLine: { lineStyle: { color: '#192536' } }, axisLabel: { fontSize: 11 } } };
        chart.setOption(report ? { ...common, legend: { data: [t("策略净值"), t("买入持有基准")], textStyle: { color: '#99abcd' }, top: 0 }, grid: { ...common.grid, top: 38 },
            series: [{ name: t("策略净值"), type: 'line', showSymbol: false, data: report.curve.map(x => Number(x.equity)), itemStyle: { color: '#5473ff' }, areaStyle: { color: '#344cff22' } },
                { name: t("买入持有基准"), type: 'line', showSymbol: false, data: report.curve.map(x => Number(x.benchmark)), lineStyle: { type: 'dashed' }, itemStyle: { color: '#31d6c6' } }] }
            : { ...common, series: [{ name: t("教学K线（开/收/低/高）"), type: 'candlestick', data: rows.map(x => [Number(x.open), Number(x.close), Number(x.low), Number(x.high)]),
                        itemStyle: { color: '#f26071', color0: '#37d4bf', borderColor: '#f26071', borderColor0: '#37d4bf' } }] });
        const resize = new ResizeObserver(() => chart.resize());
        resize.observe(ref.current);
        return () => { resize.disconnect(); chart.dispose(); };
    }, [bars, period, compact, report, locale]);
    return <div ref={ref} className={'chart ' + (compact ? 'chart-compact' : '')} role="img" aria-label={report ? t("教学策略净值与基准比较图，下方提供报告数值") : t("教学示例K线图，开盘收盘最高最低价格可在行情数据表查看")}/>;
}
