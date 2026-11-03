import unittest
import numpy as np
from experiments import get_spec

class SolarTests(unittest.TestCase):
    def test_units_missing_and_ties(self):
        from experiments.exp_lower_09_太阳能电池 import LIGHT, OUTPUT, E, current, voltage
        s=get_spec('lower_09_solar_cell'); i=s.initial_state(blank=True)
        self.assertEqual([len(t.defaults) for t in s.tables], [21,8,19])
        self.assertTrue(s.compute(i).tables['特性参数']['填充因子'].isna().all())
        i.tables[LIGHT].loc[0,E]=2580
        i.tables[OUTPUT].loc[1,current('单晶硅')]=10
        i.tables[OUTPUT].loc[2,current('单晶硅')]=5
        i.tables[OUTPUT].loc[1,voltage('单晶硅')]=.2
        i.tables[OUTPUT].loc[2,voltage('单晶硅')]=.4
        i.parameters.update(intensity=100,area=3600,voc_单晶硅=1,isc_单晶硅=10)
        r=s.compute(i); row=r.tables['特性参数'].iloc[0]
        self.assertEqual(r.tables[LIGHT].iloc[0]['光强 / (W/m²)'],100)
        self.assertEqual(row['采样最大功率 / mW'],2)
        self.assertEqual(row['最大功率点电压 / V'],'0.2、0.4')
        self.assertAlmostEqual(row['填充因子'],.2)
        self.assertAlmostEqual(row['入射功率 / mW'],360)
        self.assertAlmostEqual(row['转换效率 / %'],2/360*100)
        self.assertTrue(np.isnan(i.tables[OUTPUT].iloc[0][current('单晶硅')]))

    def test_measured_voltages_and_missing_pairs(self):
        from experiments.exp_lower_09_太阳能电池 import OUTPUT, current, voltage
        s=get_spec('lower_09_solar_cell');i=s.initial_state();r=s.compute(i)
        out=r.tables[OUTPUT]
        self.assertAlmostEqual(out.loc[0,'单晶硅功率 / mW'],.041*26.3)
        self.assertAlmostEqual(out.loc[0,'多晶硅功率 / mW'],.035*21.8)
        self.assertTrue(out.loc[18:,'单晶硅功率 / mW'].isna().all())
        self.assertTrue(out['非晶硅功率 / mW'].isna().all())
        self.assertTrue(out.loc[17:,'多晶硅功率 / mW'].isna().all())
        self.assertAlmostEqual(r.tables['特性参数'].iloc[0]['采样最大功率 / mW'],2.803*22.8)
        self.assertAlmostEqual(r.tables['特性参数'].iloc[1]['采样最大功率 / mW'],2.597*20.3)
        i.tables[OUTPUT].loc[18,current('单晶硅')]=1
        self.assertTrue(np.isnan(s.compute(i).tables[OUTPUT].loc[18,'单晶硅功率 / mW']))
        f=s.build_plot(i,s.compute(i))
        self.assertEqual(len(f.axes[3].lines),2)
        self.assertAlmostEqual(f.axes[3].lines[0].get_xdata()[0],.041)
        from matplotlib import pyplot as plt
        plt.close(f)

    def test_final_sample_efficiency_precision_and_missing_parameters(self):
        s=get_spec('lower_09_solar_cell'); i=s.initial_state(); r=s.compute(i)
        summary=r.tables['特性参数']
        self.assertAlmostEqual(summary.iloc[0]['填充因子'],63.9084/(3.381*26.7))
        self.assertAlmostEqual(summary.iloc[1]['填充因子'],52.7191/(3.3*25))
        self.assertAlmostEqual(summary.iloc[0]['转换效率 / %'],63.9084/842.4*100)
        self.assertAlmostEqual(summary.iloc[1]['转换效率 / %'],52.7191/842.4*100)
        formatted={t.title:t.frame for t in s.format_tables(i,r)}
        self.assertEqual(formatted['特性参数'].iloc[0]['采样最大功率 / mW'],'63.9')
        self.assertEqual(formatted['表9-2 光强关系'].iloc[3]['光强 / (W/m²)'],'234')
        i.parameters['isc_单晶硅']=None
        i.parameters['intensity']=None
        result=s.compute(i)
        self.assertTrue(np.isnan(result.tables['特性参数'].iloc[0]['填充因子']))
        document=s.explain(i,result)
        text='\n'.join(str(b.body) for b in document.blocks if b.kind!='image')
        self.assertIn('待录入同光照短路电流',text)
        self.assertIn('③ 计算能量转换效率',text)
        self.assertIn('待录入输出测量光强',text)
