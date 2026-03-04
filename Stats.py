import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from datetime import datetime
import re
from collections import defaultdict
import numpy as np
import os

# === ИСПРАВЛЕНИЕ: используем абсолютный путь ===
# Получаем путь к папке, где находится этот скрипт
script_dir = os.path.dirname(os.path.abspath(__file__))
log_file = os.path.join(script_dir, 'logs.txt')

print(f"Поиск лог-файла по пути: {log_file}")

# Проверяем существует ли файл
if not os.path.exists(log_file):
    print(f"❌ ОШИБКА: Файл {log_file} не найден!")
    print("\nВозможные причины:")
    print("1. Вы еще не запускали launch_all9.py для генерации логов")
    print("2. Файл был удален")
    print("3. Недостаточно прав доступа")
    exit(1)

log_entries = []

print("✅ Файл найден, читаем данные...")

with open(log_file, 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith('='):
            continue
        
        # Парсим строку лога
        # Формат: время | node_id | операция | отправитель/получатели | уточнение
        parts = line.split(' | ')
        if len(parts) >= 4:
            time_str = parts[0]
            node = parts[1]
            operation = parts[2]
            target = parts[3]
            details = parts[4] if len(parts) > 4 else ""
            
            log_entries.append({
                'time': time_str,
                'node': node,
                'operation': operation,
                'target': target,
                'details': details
            })

print(f"✅ Загружено {len(log_entries)} записей")

# 1. Статистика по операциям
def show_basic_stats():
    print("\n" + "="*50)
    print("БАЗОВАЯ СТАТИСТИКА")
    print("="*50)
    
    if not log_entries:
        print("Нет данных для анализа")
        return
    
    # Статистика по узлам
    nodes = set(entry['node'] for entry in log_entries)
    print(f"\nУзлы в сети: {', '.join(sorted(nodes))}")
    
    # Статистика по операциям
    operations = defaultdict(int)
    for entry in log_entries:
        operations[entry['operation']] += 1
    
    print("\nТоп операций:")
    for op, count in sorted(operations.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {op}: {count}")
    
    # Статистика по отправителям/получателям
    targets = defaultdict(int)
    for entry in log_entries:
        if entry['target'] != 'ALL':
            targets[entry['target']] += 1
    
    if targets:
        print("\nАктивность по узлам (как цель):")
        for target, count in sorted(targets.items(), key=lambda x: x[1], reverse=True):
            print(f"  Узел {target}: {count}")

# 2. График активности узлов во времени
def plot_node_activity():
    # Преобразуем время в секунды от начала
    if not log_entries:
        print("Нет данных для построения графиков")
        return
    
    try:
        # Берем первое время как точку отсчета
        first_time = datetime.strptime(log_entries[0]['time'], '%H:%M:%S.%f')
        
        node_activity = defaultdict(list)
        node_operations = defaultdict(lambda: defaultdict(int))
        
        for entry in log_entries:
            current_time = datetime.strptime(entry['time'], '%H:%M:%S.%f')
            time_diff = (current_time - first_time).total_seconds()
            
            node_activity[entry['node']].append(time_diff)
            node_operations[entry['node']][entry['operation']] += 1
        
        # Создаем график
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('Анализ логов сети', fontsize=16)
        
        # График 1: Активность узлов во времени
        ax1 = axes[0, 0]
        colors = {'A': 'red', 'B': 'blue', 'C': 'green', 'D': 'orange', 'E': 'purple'}
        
        y_pos = 0
        for node, times in node_activity.items():
            y_values = [y_pos] * len(times)
            ax1.scatter(times, y_values, c=colors.get(node, 'black'), label=f'Узел {node}', alpha=0.6, s=30)
            y_pos += 1
        
        ax1.set_xlabel('Время (секунды от начала)')
        ax1.set_yticks(range(len(node_activity)))
        ax1.set_yticklabels([f'Узел {node}' for node in node_activity.keys()])
        ax1.set_title('Активность узлов во времени')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        
        # График 2: Количество операций по типам
        ax2 = axes[0, 1]
        
        op_types = ['Отправка BEACON', 'Получил BEACON', 'Отправка REQUEST-PACKETS', 
                    'Получил REQUEST-PACKETS', 'Отправка PACKETS', 'Получил PACKETS']
        
        op_counts = []
        for op in op_types:
            count = sum(1 for entry in log_entries if entry['operation'] == op)
            op_counts.append(count)
        
        bars = ax2.bar(range(len(op_types)), op_counts)
        ax2.set_xticks(range(len(op_types)))
        ax2.set_xticklabels([op[:15] + '...' for op in op_types], rotation=45, ha='right')
        ax2.set_title('Типы операций')
        ax2.set_ylabel('Количество')
        
        # Добавляем значения на столбцы
        for i, (bar, count) in enumerate(zip(bars, op_counts)):
            if count > 0:
                ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                        str(count), ha='center', va='bottom', fontsize=9)
        
        # График 3: Тепловая карта передач между узлами
        ax3 = axes[1, 0]
        
        nodes_list = sorted(set(entry['node'] for entry in log_entries))
        n_nodes = len(nodes_list)
        heatmap = np.zeros((n_nodes, n_nodes))
        
        for entry in log_entries:
            if 'Отправка' in entry['operation'] and entry['target'] != 'ALL':
                try:
                    from_idx = nodes_list.index(entry['node'])
                    to_idx = nodes_list.index(entry['target'])
                    heatmap[from_idx, to_idx] += 1
                except ValueError:
                    pass
        
        im = ax3.imshow(heatmap, cmap='YlOrRd', aspect='auto')
        ax3.set_xticks(range(n_nodes))
        ax3.set_yticks(range(n_nodes))
        ax3.set_xticklabels(nodes_list)
        ax3.set_yticklabels(nodes_list)
        ax3.set_xlabel('Кому')
        ax3.set_ylabel('От кого')
        ax3.set_title('Матрица передач сообщений')
        
        # Добавляем значения в ячейки
        for i in range(n_nodes):
            for j in range(n_nodes):
                if heatmap[i, j] > 0:
                    ax3.text(j, i, int(heatmap[i, j]), ha='center', va='center', color='black', fontsize=10)
        
        plt.colorbar(im, ax=ax3)
        
        # График 4: Активность стока
        ax4 = axes[1, 1]
        
        sink_entries = [entry for entry in log_entries if entry['node'] == 'E']
        sink_ops = defaultdict(int)
        for entry in sink_entries:
            sink_ops[entry['operation']] += 1
        
        if sink_ops:
            ops = list(sink_ops.keys())
            counts = list(sink_ops.values())
            
            wedges, texts, autotexts = ax4.pie(counts, labels=ops, autopct='%1.1f%%', startangle=90)
            ax4.set_title('Активность стока (узел E)')
        else:
            ax4.text(0.5, 0.5, 'Нет данных', ha='center', va='center')
            ax4.set_title('Активность стока (узел E)')
        
        plt.tight_layout()
        plt.show()
        
    except Exception as e:
        print(f"Ошибка при построении графиков: {e}")

# 3. Диаграмма потока пакетов
def plot_packet_flow():
    if not log_entries:
        return
    
    # Извлекаем информацию о передаче пакетов
    packet_transfers = []
    
    for entry in log_entries:
        if 'PACKETS' in entry['operation'] and entry['details'] and entry['details'] != 'None':
            # Пытаемся извлечь номера пакетов из details
            match = re.search(r'\[(.*?)\]', entry['details'])
            if match:
                packets = match.group(1)
                packet_transfers.append({
                    'from': entry['node'],
                    'to': entry['target'] if entry['target'] != 'ALL' else 'broadcast',
                    'packets': packets,
                    'time': entry['time']
                })
    
    if not packet_transfers:
        print("Нет данных о передаче пакетов")
        return
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Визуализируем передачи
    y_pos = 0
    
    for transfer in packet_transfers[:20]:  # Ограничим для наглядности
        
        from_node = transfer['from']
        to_node = transfer['to']
        
        color = 'green' if to_node == 'broadcast' else 'blue'
        
        ax.annotate('', xy=(y_pos, 1), xytext=(y_pos, 0),
                   arrowprops=dict(arrowstyle='->', color=color, lw=1))
        
        ax.text(y_pos, 1.1, f"{from_node}→{to_node}\n{transfer['packets']}", 
               ha='center', fontsize=8, rotation=45)
        
        y_pos += 1
    
    ax.set_xlim(-1, y_pos)
    ax.set_ylim(-0.5, 1.5)
    ax.set_title('Поток пакетов (первые 20 передач)')
    ax.set_xlabel('Номер передачи')
    ax.set_yticks([])
    ax.grid(True, alpha=0.3, axis='x')
    
    plt.tight_layout()
    plt.show()

# 4. Сохраняем статистику в файл
def save_stats_to_file():
    if not log_entries:
        print("Нет данных для сохранения")
        return
    
    stats_file = os.path.join(script_dir, 'network_stats.txt')
    
    with open(stats_file, 'w', encoding='utf-8') as f:
        f.write("="*60 + "\n")
        f.write("СТАТИСТИКА РАБОТЫ СЕТИ\n")
        f.write(f"Сгенерировано: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Источник: {log_file}\n")
        f.write("="*60 + "\n\n")
        
        f.write(f"Всего записей в логе: {len(log_entries)}\n\n")
        
        # Статистика по узлам
        nodes = sorted(set(entry['node'] for entry in log_entries))
        f.write("УЗЛЫ:\n")
        for node in nodes:
            node_entries = [e for e in log_entries if e['node'] == node]
            f.write(f"  Узел {node}: {len(node_entries)} операций\n")
        
        f.write("\nТИПЫ ОПЕРАЦИЙ:\n")
        operations = defaultdict(int)
        for entry in log_entries:
            operations[entry['operation']] += 1
        
        for op, count in sorted(operations.items(), key=lambda x: x[1], reverse=True):
            f.write(f"  {op}: {count}\n")
        
        f.write("\nПЕРЕДАЧИ МЕЖДУ УЗЛАМИ:\n")
        transfers = defaultdict(int)
        for entry in log_entries:
            if 'Отправка' in entry['operation'] and entry['target'] != 'ALL':
                key = f"{entry['node']} → {entry['target']}"
                transfers[key] += 1
        
        for transfer, count in sorted(transfers.items(), key=lambda x: x[1], reverse=True):
            f.write(f"  {transfer}: {count}\n")
    
    print(f"\n✅ Статистика сохранена в {stats_file}")

# Запуск визуализации
if __name__ == "__main__":
    print("\n" + "="*60)
    print("ВИЗУАЛИЗАТОР ЛОГОВ СЕТИ")
    print("="*60)
    
    if log_entries:
        show_basic_stats()
        
        print("\n" + "="*50)
        print("МЕНЮ ВИЗУАЛИЗАЦИИ")
        print("="*50)
        print("1. Показать базовую статистику")
        print("2. Показать графики активности")
        print("3. Показать поток пакетов")
        print("4. Сохранить статистику в файл")
        print("5. Всё вместе")
        print("0. Выход")
        
        choice = input("\nВыберите действие (0-5): ").strip()
        
        if choice == '1':
            show_basic_stats()
        elif choice == '2':
            plot_node_activity()
        elif choice == '3':
            plot_packet_flow()
        elif choice == '4':
            save_stats_to_file()
        elif choice == '5':
            show_basic_stats()
            plot_node_activity()
            plot_packet_flow()
            save_stats_to_file()
        elif choice == '0':
            print("Выход...")
        else:
            print("Неверный выбор, показываю всё...")
            show_basic_stats()
            plot_node_activity()
            plot_packet_flow()
            save_stats_to_file()
    else:
        print("\n❌ Нет данных для визуализации.")
        print("Сначала запустите launch_all9.py для генерации логов.")