from __future__ import annotations

import itertools
import math
from collections import deque
from enum import Enum, auto
from typing import NamedTuple

牌库数量元组 = (5, 5, 5, 8, 6)
演算奖励元组 = (0, 1000, 2000, 4000, 7500, 12000, 20000, 36000, 60000, 100000, 160000)


class 决策空间类(Enum):
    抽取铭牌 = auto()
    放弃 = auto()
    开始演算 = auto()
    翻倍 = auto()  # 仅手牌=2 且未翻倍时可选择


type 状态类 = 过渡态类 | 吸收态类


class 过渡态类(NamedTuple):
    剩余演算次数: int
    剩余放弃次数: int
    剩余翻倍次数: int
    是否翻倍: bool
    已抽到的铭牌数量元组: tuple[int, ...]


class 吸收态类(Enum):
    已结束 = auto()


def 计算战力点(已抽到的铭牌数量元组: tuple[int, ...]) -> int:
    return (
        sum((i + 1) * 铭牌数量 for i, 铭牌数量 in enumerate(已抽到的铭牌数量元组)) % 11
    )


class MDPResult(NamedTuple):
    """MDP 求解结果"""

    价值函数: list[float]
    最优策略: list[决策空间类 | None]
    状态列表: list[状态类]
    状态索引: dict[状态类, int]

    def 打印最优策略(self, 最多显示: int = 20) -> None:
        已打印 = 0
        for i, 状态 in enumerate(self.状态列表):
            if isinstance(状态, 吸收态类):
                continue
            决策 = self.最优策略[i]
            价值 = self.价值函数[i]
            if 决策 is not None:
                print(f"状态 {i:5d}: {状态!s:80s}  → {决策.name:8s}  v*={价值:12.2f}")
                已打印 += 1
                if 已打印 >= 最多显示:
                    break
        if 已打印 < sum(1 for s in self.状态列表 if not isinstance(s, 吸收态类)):
            print(
                f"  ... 共 {sum(1 for s in self.状态列表 if not isinstance(s, 吸收态类))} 个过渡态"
            )

    def 导出CSV(self, 文件路径: str = "strategy_simplified.csv") -> None:
        """将最优策略导出为 CSV 文件"""
        import csv

        with open(文件路径, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "状态序号",
                    "剩余演算次数",
                    "剩余放弃次数",
                    "剩余翻倍次数",
                    "是否翻倍",
                    "点数1手牌数量",
                    "点数2手牌数量",
                    "点数3手牌数量",
                    "点数4手牌数量",
                    "点数5手牌数量",
                    "手牌总数",
                    "战力点",
                    "最优决策",
                    "最优价值",
                ]
            )
            for i, 状态 in enumerate(self.状态列表):
                if isinstance(状态, 吸收态类):
                    continue
                决策 = self.最优策略[i]
                价值 = self.价值函数[i]
                if 决策 is None:
                    continue
                手牌 = 状态.已抽到的铭牌数量元组
                手牌总数 = sum(手牌)
                战力点 = 计算战力点(手牌)
                writer.writerow(
                    [
                        i,
                        状态.剩余演算次数,
                        状态.剩余放弃次数,
                        状态.剩余翻倍次数,
                        状态.是否翻倍,
                        *手牌,
                        手牌总数,
                        战力点,
                        决策.name,
                        round(价值, 2),
                    ]
                )
        print(
            f"\n策略已导出到: {文件路径} ({sum(1 for s in self.状态列表 if not isinstance(s, 吸收态类))} 个状态)"
        )


class 求解器类:
    def __init__(
        self,
        *,
        牌库数量元组: tuple[int, ...],
        演算奖励元组: tuple[int, ...],
    ):
        self.牌库数量元组 = 牌库数量元组
        self.演算奖励元组 = 演算奖励元组

    def 已抽到的铭牌数量组合(self) -> list[tuple[int, ...]]:
        return [
            组合
            for 组合 in itertools.product(*(range(n + 1) for n in self.牌库数量元组))
            if sum(组合) <= 5
        ]

    def 计算演算奖励(
        self, 已抽到的铭牌数量元组: tuple[int, ...], 是否翻倍: bool
    ) -> float:
        战力点 = 计算战力点(已抽到的铭牌数量元组)
        演算奖励 = self.演算奖励元组[战力点]
        if 是否翻倍:
            演算奖励 *= 2
        return 演算奖励

    def 获取状态(
        self,
        *,
        剩余演算次数: int,
        剩余放弃次数: int,
        剩余翻倍次数: int,
        是否翻倍: bool,
        已抽到的铭牌数量元组: tuple[int, ...],
    ) -> 状态类:
        if 剩余演算次数 == 0:
            return 吸收态类.已结束
        return 过渡态类(
            剩余演算次数=剩余演算次数,
            剩余放弃次数=剩余放弃次数,
            剩余翻倍次数=剩余翻倍次数,
            是否翻倍=是否翻倍,
            已抽到的铭牌数量元组=已抽到的铭牌数量元组,
        )

    def 状态转移(
        self, *, 起始状态: 状态类, 决策: 决策空间类
    ) -> list[tuple[状态类, float]]:
        转移概率列表: list[tuple[状态类, float]] = []

        if isinstance(起始状态, 吸收态类):
            转移概率列表.append((起始状态, 1.0))
            return 转移概率列表

        起始剩余演算次数 = 起始状态.剩余演算次数
        起始剩余放弃次数 = 起始状态.剩余放弃次数
        起始剩余翻倍次数 = 起始状态.剩余翻倍次数
        起始是否翻倍 = 起始状态.是否翻倍
        起始已抽到的铭牌数量元组 = 起始状态.已抽到的铭牌数量元组

        match 决策:
            case 决策空间类.抽取铭牌:
                剩余铭牌数量元组 = tuple(
                    self.牌库数量元组[i] - 起始已抽到的铭牌数量元组[i] for i in range(5)
                )
                总剩余铭牌数量 = sum(剩余铭牌数量元组)
                for i, 该点数剩余铭牌数量 in enumerate(剩余铭牌数量元组):
                    if 该点数剩余铭牌数量 > 0:
                        概率 = 该点数剩余铭牌数量 / 总剩余铭牌数量
                        目标已抽到的铭牌数量元组 = tuple(
                            起始已抽到的铭牌数量元组[j] + (1 if j == i else 0)
                            for j in range(5)
                        )
                        目标状态 = self.获取状态(
                            剩余演算次数=起始剩余演算次数,
                            剩余放弃次数=起始剩余放弃次数,
                            剩余翻倍次数=起始剩余翻倍次数,
                            是否翻倍=起始是否翻倍,
                            已抽到的铭牌数量元组=目标已抽到的铭牌数量元组,
                        )
                        转移概率列表.append((目标状态, 概率))

            case 决策空间类.放弃:
                if 起始剩余放弃次数 > 0:
                    目标状态 = self.获取状态(
                        剩余演算次数=起始剩余演算次数,
                        剩余放弃次数=起始剩余放弃次数 - 1,
                        剩余翻倍次数=起始剩余翻倍次数,
                        是否翻倍=False,  # 重置为未翻倍
                        已抽到的铭牌数量元组=(0, 0, 0, 0, 0),
                    )
                    转移概率列表.append((目标状态, 1.0))
                else:
                    目标状态 = self.获取状态(
                        剩余演算次数=起始剩余演算次数 - 1,
                        剩余放弃次数=起始剩余放弃次数,
                        剩余翻倍次数=起始剩余翻倍次数,
                        是否翻倍=False,  # 重置为未翻倍
                        已抽到的铭牌数量元组=(0, 0, 0, 0, 0),
                    )
                    转移概率列表.append((目标状态, 1.0))

            case 决策空间类.开始演算:
                目标状态 = self.获取状态(
                    剩余演算次数=起始剩余演算次数 - 1,
                    剩余放弃次数=起始剩余放弃次数,
                    剩余翻倍次数=起始剩余翻倍次数 - (1 if 起始是否翻倍 else 0),
                    是否翻倍=False,  # 重置为未翻倍
                    已抽到的铭牌数量元组=(0, 0, 0, 0, 0),
                )
                转移概率列表.append((目标状态, 1.0))

            case 决策空间类.翻倍:
                # 翻倍：将翻倍状态设为 True
                目标状态 = self.获取状态(
                    剩余演算次数=起始剩余演算次数,
                    剩余放弃次数=起始剩余放弃次数,
                    剩余翻倍次数=起始剩余翻倍次数,
                    是否翻倍=True,
                    已抽到的铭牌数量元组=起始已抽到的铭牌数量元组,
                )
                转移概率列表.append((目标状态, 1.0))

        转移概率列表 = [(目标状态, 概率) for 目标状态, 概率 in 转移概率列表 if 概率 > 0]
        assert math.isclose(sum(x[1] for x in 转移概率列表), 1), (
            f"转移概率之和不为 1。起始状态: {起始状态}, 决策: {决策}, 转移概率列表: {转移概率列表}，概率之和: {sum(x[1] for x in 转移概率列表)}"
        )
        return 转移概率列表

    def 状态容许决策(self, 状态: 状态类) -> list[决策空间类]:
        if isinstance(状态, 吸收态类):
            return []

        已抽到的铭牌总数量 = sum(状态.已抽到的铭牌数量元组)

        if 已抽到的铭牌总数量 == 5:
            # 手牌满：只能开始演算或放弃
            return [决策空间类.开始演算, 决策空间类.放弃]

        # 基础决策：所有非手牌满状态下都有
        基础决策 = [决策空间类.抽取铭牌, 决策空间类.放弃, 决策空间类.开始演算]

        if 已抽到的铭牌总数量 == 2 and not 状态.是否翻倍 and 状态.剩余翻倍次数 > 0:
            # 手牌=2 且未翻倍且有翻倍次数：可以翻倍
            return [*基础决策, 决策空间类.翻倍]

        # 其余情况：不能翻倍
        return 基础决策

    def 行动奖励(self, 状态: 状态类, 决策: 决策空间类) -> float:
        if isinstance(状态, 吸收态类):
            return 0.0

        if 决策 == 决策空间类.开始演算:
            return self.计算演算奖励(
                已抽到的铭牌数量元组=状态.已抽到的铭牌数量元组,
                是否翻倍=状态.是否翻倍,
            )

        return 0.0

    def 是需要考虑的状态(self, 状态: 过渡态类) -> bool:
        if not (
            1 <= 状态.剩余演算次数 <= 3
            and 0 <= 状态.剩余放弃次数 <= 3
            and 状态.剩余演算次数 - 1 <= 状态.剩余翻倍次数 <= 2
        ):
            return False

        已抽到的铭牌总数量 = sum(状态.已抽到的铭牌数量元组)
        if 已抽到的铭牌总数量 <= 1 and 状态.是否翻倍:
            # 手牌 <= 1 时，必须为未翻倍状态
            return False
        if 已抽到的铭牌总数量 == 2 and 状态.是否翻倍 and 状态.剩余翻倍次数 == 0:
            # 手牌=2 且已翻倍但没有翻倍次数了（不合逻辑，翻倍后应消耗次数）
            return False

        return True

    def 构建状态列表(self) -> None:
        self.状态列表: list[状态类] = []
        self.状态列表.extend(吸收态类)
        self.状态列表.extend(
            过渡态类(
                剩余演算次数=剩余演算次数,
                剩余放弃次数=剩余放弃次数,
                剩余翻倍次数=剩余翻倍次数,
                是否翻倍=是否翻倍,
                已抽到的铭牌数量元组=已抽到的铭牌数量元组,
            )
            for 剩余演算次数 in range(1, 3 + 1)
            for 剩余放弃次数 in range(0, 3 + 1)
            for 剩余翻倍次数 in range(0, 2 + 1)
            for 是否翻倍 in (False, True)
            for 已抽到的铭牌数量元组 in self.已抽到的铭牌数量组合()
            if self.是需要考虑的状态(
                过渡态类(
                    剩余演算次数=剩余演算次数,
                    剩余放弃次数=剩余放弃次数,
                    剩余翻倍次数=剩余翻倍次数,
                    是否翻倍=是否翻倍,
                    已抽到的铭牌数量元组=已抽到的铭牌数量元组,
                )
            )
        )

        self.状态数量: int = len(self.状态列表)
        self.状态索引: dict[状态类, int] = {
            状态: i for i, 状态 in enumerate(self.状态列表)
        }

    def 构建单个状态转移矩阵(self, 决策: 决策空间类) -> list[tuple[int, float]]:
        result = []
        for 起始状态 in self.状态列表:
            line = []
            转移概率列表 = self.状态转移(起始状态=起始状态, 决策=决策)
            for 目标状态, 概率 in 转移概率列表:
                目标状态序号 = self.状态索引[目标状态]
                line.append((目标状态序号, 概率))
            result.append(line)
        return result

    def 构建状态转移矩阵(self) -> None:
        self.状态转移矩阵字典: dict[决策空间类, list[tuple[int, float]]] = {
            决策: self.构建单个状态转移矩阵(决策=决策) for 决策 in 决策空间类
        }

    def 构建状态容许决策列表(self) -> None:
        self.状态容许决策列表: list[list[决策空间类]] = []
        for 状态 in self.状态列表:
            容许决策列表 = self.状态容许决策(状态=状态)
            self.状态容许决策列表.append(容许决策列表)

    def 求解MDP(self) -> MDPResult:
        """求解 MDP，返回最优价值函数 v* 和最优策略 π*"""

        self.构建状态列表()
        self.构建状态容许决策列表()

        N = self.状态数量
        状态列表 = self.状态列表
        状态索引 = self.状态索引

        # 1. 拓扑排序：从吸收态反向BFS计算距离
        反向边: list[list[int]] = [[] for _ in range(N)]
        for 起始序号, 起始状态 in enumerate(状态列表):
            for 决策 in self.状态容许决策列表[起始序号]:
                转移 = self.状态转移(起始状态=起始状态, 决策=决策)
                for 目标状态, _ in 转移:
                    反向边[状态索引[目标状态]].append(起始序号)

        吸收态序号列表 = [i for i, s in enumerate(状态列表) if isinstance(s, 吸收态类)]
        距离 = [-1] * N
        q = deque()
        for idx in 吸收态序号列表:
            距离[idx] = 0
            q.append(idx)
        while q:
            目标 = q.popleft()
            for 源 in 反向边[目标]:
                if 距离[源] < 距离[目标] + 1:
                    距离[源] = 距离[目标] + 1
                    q.append(源)

        # 2. 按距离从小到大 DP 求解 v*
        排序序号 = sorted(range(N), key=lambda i: 距离[i])
        价值函数 = [0.0] * N
        最优策略: list[决策空间类 | None] = [None] * N

        for 序号 in 排序序号:
            状态 = 状态列表[序号]
            if isinstance(状态, 吸收态类):
                价值函数[序号] = 0.0
                最优策略[序号] = None
                continue

            最佳价值 = -float("inf")
            最佳决策 = None
            for 决策 in self.状态容许决策列表[序号]:
                即时奖励 = self.行动奖励(状态=状态, 决策=决策)
                期望未来价值 = 0.0
                for 目标状态, 概率 in self.状态转移(起始状态=状态, 决策=决策):
                    期望未来价值 += 概率 * 价值函数[状态索引[目标状态]]
                总价值 = 即时奖励 + 期望未来价值
                if 总价值 > 最佳价值 + 1e-10:
                    最佳价值 = 总价值
                    最佳决策 = 决策

            价值函数[序号] = 最佳价值
            最优策略[序号] = 最佳决策

        return MDPResult(
            价值函数=价值函数,
            最优策略=最优策略,
            状态列表=状态列表,
            状态索引=状态索引,
        )


if __name__ == "__main__":
    求解器 = 求解器类(
        牌库数量元组=牌库数量元组,
        演算奖励元组=演算奖励元组,
    )
    result = 求解器.求解MDP()

    初始状态 = 过渡态类(
        剩余演算次数=3,
        剩余放弃次数=3,
        剩余翻倍次数=2,
        是否翻倍=False,
        已抽到的铭牌数量元组=(0, 0, 0, 0, 0),
    )
    初始序号 = result.状态索引[初始状态]

    print(f"\n{'=' * 60}")
    print("【简化版】最优策略求解结果")
    print(f"{'=' * 60}")
    print(f"\n初始状态最优价值 v*(初始) = {result.价值函数[初始序号]:,.2f}")
    print(f"初始状态最优决策 π*(初始) = {result.最优策略[初始序号].name}")
    print(f"\n总状态数: {len(result.状态列表)}")

    result.导出CSV("strategy_simplified.csv")
