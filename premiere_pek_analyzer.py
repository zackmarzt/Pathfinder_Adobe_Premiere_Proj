"""
Analisador de arquivos PEK (Peak Audio Files) do Adobe Premiere Pro
Extrai informações sobre forma de onda, duração e metadados
"""
import os
import struct
from pathlib import Path
from datetime import datetime, timedelta

class PEKAnalyzer:
    """Classe para analisar arquivos .pek do Premiere Pro"""

    def __init__(self, file_path):
        self.file_path = file_path
        self.header = {}
        self.peaks = []
        self.metadata = {}

    def read_pek_file(self):
        """Lê e analisa o arquivo PEK"""
        try:
            with open(self.file_path, 'rb') as f:
                # Ler informações do arquivo
                file_size = os.path.getsize(self.file_path)

                # Tentar diferentes formatos de PEK
                # O formato pode variar entre versões do Premiere

                # Ler os primeiros bytes para identificar o formato
                magic_bytes = f.read(4)
                f.seek(0)

                # Formato básico de análise
                self._parse_basic_structure(f, file_size)

                return True

        except Exception as e:
            self.metadata['error'] = str(e)
            return False

    def _parse_basic_structure(self, f, file_size):
        """Analisa a estrutura básica do arquivo PEK"""
        # Ler header (primeiros bytes)
        header_data = f.read(512)  # Ler primeiros 512 bytes como header

        # Tentar identificar padrões comuns
        self.metadata['file_size'] = file_size
        self.metadata['file_size_formatted'] = self.format_size(file_size)

        # Ler dados brutos para análise
        f.seek(0)
        all_data = f.read()

        # Tentar encontrar padrões de audio peaks
        # PEK files geralmente armazenam valores de pico em formato binário
        self._analyze_peak_data(all_data)

        # Tentar extrair informações de timing
        self._extract_timing_info(all_data)

    def _analyze_peak_data(self, data):
        """Analisa os dados de pico de áudio"""
        # Tentar interpretar como valores float (32-bit)
        num_floats = len(data) // 4

        try:
            # Ler como floats
            float_values = []
            for i in range(0, len(data) - 3, 4):
                try:
                    value = struct.unpack('<f', data[i:i+4])[0]
                    if -1.0 <= value <= 1.0:  # Valores de áudio normalizados
                        float_values.append(value)
                except:
                    continue

            if float_values:
                self.peaks = float_values
                self.metadata['peak_count'] = len(float_values)
                self.metadata['max_peak'] = max(float_values) if float_values else 0
                self.metadata['min_peak'] = min(float_values) if float_values else 0
                self.metadata['avg_peak'] = sum(abs(v) for v in float_values) / len(float_values) if float_values else 0
        except:
            pass

        # Tentar interpretar como valores short (16-bit)
        try:
            short_values = []
            for i in range(0, len(data) - 1, 2):
                try:
                    value = struct.unpack('<h', data[i:i+2])[0]
                    if -32768 <= value <= 32767:
                        short_values.append(value / 32768.0)  # Normalizar
                except:
                    continue

            if len(short_values) > len(float_values):
                self.peaks = short_values
                self.metadata['peak_count'] = len(short_values)
                self.metadata['max_peak'] = max(short_values) if short_values else 0
                self.metadata['min_peak'] = min(short_values) if short_values else 0
                self.metadata['avg_peak'] = sum(abs(v) for v in short_values) / len(short_values) if short_values else 0
        except:
            pass

    def _extract_timing_info(self, data):
        """Tenta extrair informações de duração e timing"""
        # Procurar por valores que possam indicar sample rate ou duração
        # Valores comuns: 44100, 48000, 96000 Hz

        common_sample_rates = [44100, 48000, 96000, 88200, 192000]

        for i in range(0, len(data) - 3, 1):
            try:
                # Tentar ler como int32
                value = struct.unpack('<I', data[i:i+4])[0]
                if value in common_sample_rates:
                    self.metadata['possible_sample_rate'] = value
                    break
            except:
                continue

    def get_audio_info(self):
        """Retorna informações extraídas do áudio"""
        info = {
            'file_name': os.path.basename(self.file_path),
            'file_path': self.file_path,
            'file_size': self.metadata.get('file_size', 0),
            'file_size_formatted': self.metadata.get('file_size_formatted', '0 B'),
        }

        # Adicionar informações de pico se disponíveis
        if 'peak_count' in self.metadata:
            info['peak_samples'] = self.metadata['peak_count']
            info['max_amplitude'] = f"{self.metadata['max_peak']:.4f}"
            info['min_amplitude'] = f"{self.metadata['min_peak']:.4f}"
            info['avg_amplitude'] = f"{self.metadata['avg_peak']:.4f}"

            # Estimar duração baseado em sample rate
            if 'possible_sample_rate' in self.metadata:
                sample_rate = self.metadata['possible_sample_rate']
                duration_seconds = self.metadata['peak_count'] / sample_rate
                info['estimated_duration'] = str(timedelta(seconds=int(duration_seconds)))
                info['sample_rate'] = f"{sample_rate} Hz"

        # Adicionar informações do arquivo
        try:
            stat = os.stat(self.file_path)
            info['created'] = datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S')
            info['modified'] = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        except:
            pass

        return info

    def export_waveform_data(self, output_file, max_points=1000):
        """Exporta dados de forma de onda para visualização"""
        if not self.peaks:
            return False

        # Reduzir pontos para visualização se necessário
        step = max(1, len(self.peaks) // max_points)
        reduced_peaks = self.peaks[::step]

        with open(output_file, 'w') as f:
            f.write("# Waveform data from PEK file\n")
            f.write(f"# Source: {self.file_path}\n")
            f.write(f"# Total samples: {len(self.peaks)}\n")
            f.write(f"# Displayed samples: {len(reduced_peaks)}\n")
            f.write("# Format: sample_index,amplitude\n\n")

            for i, peak in enumerate(reduced_peaks):
                f.write(f"{i * step},{peak:.6f}\n")

        return True

    def create_ascii_waveform(self, width=80, height=20):
        """Cria uma visualização ASCII da forma de onda"""
        if not self.peaks:
            return "Nenhum dado de forma de onda disponível"

        # Reduzir para largura desejada
        step = max(1, len(self.peaks) // width)
        reduced_peaks = self.peaks[::step][:width]

        # Normalizar para altura
        if reduced_peaks:
            max_val = max(abs(min(reduced_peaks)), abs(max(reduced_peaks)))
            if max_val > 0:
                normalized = [int((p / max_val) * (height // 2)) for p in reduced_peaks]
            else:
                normalized = [0] * len(reduced_peaks)
        else:
            normalized = []

        # Criar grid ASCII
        lines = []
        for row in range(height // 2, -(height // 2), -1):
            line = ""
            for val in normalized:
                if val >= row > 0 or val <= row < 0:
                    line += "█"
                elif row == 0:
                    line += "─"
                else:
                    line += " "
            lines.append(line)

        return "\n".join(lines)

    @staticmethod
    def format_size(size_bytes):
        """Formata tamanho em bytes"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"


def analyze_pek_file(file_path):
    """Analisa um arquivo PEK individual"""
    analyzer = PEKAnalyzer(file_path)

    if analyzer.read_pek_file():
        return analyzer
    else:
        return None


def find_and_analyze_pek_files(search_path=None):
    """Encontra e analisa todos os arquivos PEK"""
    if search_path is None:
        search_path = os.getcwd()

    pek_files = []

    print(f"Buscando arquivos .pek em: {search_path}")
    print("=" * 80)

    for root, dirs, files in os.walk(search_path):
        # Filtrar diretórios do sistema
        dirs[:] = [d for d in dirs if not d.startswith('.') and
                  d not in ['Windows', 'System Volume Information', '$Recycle.Bin']]

        for file in files:
            if file.lower().endswith('.pek'):
                file_path = os.path.join(root, file)
                pek_files.append(file_path)
                print(f"✓ Encontrado: {file_path}")

    return pek_files


def main():
    """Função principal"""
    print("=" * 80)
    print("ANALISADOR DE ARQUIVOS PEK DO ADOBE PREMIERE PRO")
    print("=" * 80)
    print()

    print("Opções:")
    print("1 - Analisar um arquivo PEK específico")
    print("2 - Buscar e analisar todos os arquivos PEK em um diretório")
    print("3 - Usar o último scan de arquivos do Premiere")

    try:
        choice = input("\nEscolha uma opção (1-3): ").strip()

        if choice == "1":
            file_path = input("Digite o caminho completo do arquivo .pek: ").strip()
            if not os.path.exists(file_path):
                print(f"Erro: Arquivo não encontrado: {file_path}")
                return

            print(f"\nAnalisando: {file_path}")
            print("-" * 80)

            analyzer = analyze_pek_file(file_path)

            if analyzer:
                info = analyzer.get_audio_info()

                print("\nINFORMAÇÕES DO ARQUIVO:")
                print("-" * 80)
                for key, value in info.items():
                    print(f"{key.replace('_', ' ').title()}: {value}")

                # Mostrar forma de onda ASCII
                if analyzer.peaks:
                    print("\nFORMA DE ONDA (ASCII):")
                    print("-" * 80)
                    print(analyzer.create_ascii_waveform(width=80, height=20))

                    # Oferecer exportação
                    export = input("\nDeseja exportar os dados da forma de onda? (s/n): ").strip().lower()
                    if export == 's':
                        output_file = input("Nome do arquivo de saída [waveform_data.csv]: ").strip() or "waveform_data.csv"
                        if analyzer.export_waveform_data(output_file):
                            print(f"\n✓ Dados exportados para: {os.path.abspath(output_file)}")
            else:
                print("Erro ao analisar o arquivo.")

        elif choice == "2":
            search_path = input("Digite o diretório para buscar (Enter para diretório atual): ").strip()
            if not search_path:
                search_path = os.getcwd()

            if not os.path.exists(search_path):
                print(f"Erro: Diretório não encontrado: {search_path}")
                return

            print()
            pek_files = find_and_analyze_pek_files(search_path)

            if not pek_files:
                print("\nNenhum arquivo .pek encontrado.")
                return

            print(f"\n{'='*80}")
            print(f"Encontrados {len(pek_files)} arquivo(s) .pek")
            print(f"{'='*80}\n")

            # Analisar todos
            results = []
            for i, pek_file in enumerate(pek_files, 1):
                print(f"\nAnalisando {i}/{len(pek_files)}: {os.path.basename(pek_file)}")
                analyzer = analyze_pek_file(pek_file)
                if analyzer:
                    results.append(analyzer.get_audio_info())

            # Gerar relatório
            if results:
                report_file = "pek_analysis_report.txt"
                with open(report_file, 'w', encoding='utf-8') as f:
                    f.write("=" * 100 + "\n")
                    f.write("RELATÓRIO DE ANÁLISE DE ARQUIVOS PEK\n")
                    f.write(f"Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("=" * 100 + "\n\n")

                    for info in results:
                        f.write("-" * 100 + "\n")
                        for key, value in info.items():
                            f.write(f"{key.replace('_', ' ').title()}: {value}\n")
                        f.write("\n")

                print(f"\n✓ Relatório salvo em: {os.path.abspath(report_file)}")

        elif choice == "3":
            print("\nProcurando resultados do scan anterior...")

            # Procurar pelo último arquivo JSON gerado
            scan_dir = "premiere_scan_results"
            if os.path.exists(scan_dir):
                import json
                json_files = [f for f in os.listdir(scan_dir) if f.startswith('premiere_data_') and f.endswith('.json')]

                if json_files:
                    latest_json = sorted(json_files)[-1]
                    json_path = os.path.join(scan_dir, latest_json)

                    print(f"Carregando: {json_path}")

                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    pek_files = [f['path'] for f in data['files'] if f['extension'] == '.pek']

                    if pek_files:
                        print(f"\nEncontrados {len(pek_files)} arquivos .pek no scan anterior")

                        analyze = input("Deseja analisar todos? (s/n): ").strip().lower()
                        if analyze == 's':
                            results = []
                            for i, pek_file in enumerate(pek_files, 1):
                                print(f"\nAnalisando {i}/{len(pek_files)}: {os.path.basename(pek_file)}")
                                analyzer = analyze_pek_file(pek_file)
                                if analyzer:
                                    results.append(analyzer.get_audio_info())

                            if results:
                                report_file = "pek_analysis_report.txt"
                                with open(report_file, 'w', encoding='utf-8') as f:
                                    f.write("=" * 100 + "\n")
                                    f.write("RELATÓRIO DE ANÁLISE DE ARQUIVOS PEK\n")
                                    f.write(f"Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                                    f.write("=" * 100 + "\n\n")

                                    for info in results:
                                        f.write("-" * 100 + "\n")
                                        for key, value in info.items():
                                            f.write(f"{key.replace('_', ' ').title()}: {value}\n")
                                        f.write("\n")

                                print(f"\n✓ Relatório salvo em: {os.path.abspath(report_file)}")
                    else:
                        print("Nenhum arquivo .pek encontrado no scan anterior.")
                else:
                    print("Nenhum arquivo de scan encontrado.")
            else:
                print(f"Diretório '{scan_dir}' não encontrado. Execute primeiro o scan completo.")

        else:
            print("Opção inválida.")

    except KeyboardInterrupt:
        print("\n\nOperação cancelada pelo usuário.")
    except Exception as e:
        print(f"\nErro: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
