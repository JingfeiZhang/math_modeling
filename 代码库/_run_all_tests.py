# -*- coding: utf-8 -*-
"""批量测试：用当前 Python 逐个运行所有算法模板，报告通过/失败。"""
import subprocess, sys, os, glob, io

os.environ['MPLBACKEND'] = 'Agg'          # 不弹窗
os.environ['PYTHONIOENCODING'] = 'utf-8'  # 避免 GBK 乱码

root = os.path.dirname(os.path.abspath(__file__))
py_files = sorted(glob.glob(os.path.join(root, '*', '*.py')))

results = []
for f in py_files:
    rel = os.path.relpath(f, root)
    try:
        p = subprocess.run([sys.executable, f], capture_output=True,
                           text=True, encoding='utf-8', errors='replace',
                           timeout=300, cwd=os.path.dirname(f))
        if p.returncode == 0:
            results.append(('PASS', rel, ''))
        else:
            # 取 stderr 最后几行作为错误摘要
            err = (p.stderr or '').strip().splitlines()
            tail = ' | '.join(err[-3:]) if err else 'returncode=%d' % p.returncode
            results.append(('FAIL', rel, tail))
    except subprocess.TimeoutExpired:
        results.append(('TIMEOUT', rel, '>300s'))
    except Exception as e:
        results.append(('ERROR', rel, repr(e)))

print('\n================ 测试结果 ================')
for status, rel, msg in results:
    print(f'[{status:7s}] {rel}')
    if msg:
        print(f'          -> {msg}')

n_pass = sum(1 for r in results if r[0] == 'PASS')
print(f'\n合计: {n_pass}/{len(results)} 通过')
