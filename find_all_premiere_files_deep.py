"""
Script de busca profunda para TODOS os arquivos relacionados ao Adobe Premiere Pro
Busca em TODOS os discos disponíveis no sistema
"""
import os
import sys
import string
from pathlib import Path
from datetime import datetime
import json

def get_available_drives():
    """Detecta todos os drives disponíveis no sistema"""
    drives = []

    if os.name == 'nt':  # Windows
        # Testar todas as letras de A a Z
        for letter in string.ascii_uppercase:
            drive = f"{letter}:\\"
            if os.path.exists(drive):
                try:
                    # Verificar se é acessível
                    os.listdir(drive)
                    drives.append(drive)
                except (PermissionError, OSError):
                    # Drive existe mas não é acessível (ex: CD-ROM vazio)
                    pass
    else:  # Linux/Mac
        drives = ['/']
        # Adicionar pontos de montagem comuns
        mount_points = ['/mnt', '/media']
        for mp in mount_points:
            if os.path.exists(mp):
                try:
                    for item in os.listdir(mp):
                        path = os.path.join(mp, item)
                        if os.path.ismount(path):
                            drives.append(path)
                except (PermissionError, OSError):
                    pass

    return drives

def format_size(size_bytes):
    """Formata o tamanho em bytes para uma forma legível"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"

def get_premiere_extensions():
    """Retorna todas as extensões relacionadas ao Adobe Premiere Pro"""
    return {
        # Arquivos de projeto
        '.prproj': 'Projeto do Premiere Pro',
        '.prel': 'Biblioteca de Premiere Elements',
        '.prfpset': 'Preset de Efeitos do Premiere',
        '.prtpset': 'Preset de Título do Premiere',
        '.prtl': 'Template de Título do Premiere',

        # Arquivos de cache e mídia
        '.pek': 'Peak Audio File',
        '.cfa': 'Conformed Audio File',
        '.mcache': 'Media Cache',
        '.ims': 'Importer State',

        # Arquivos de backup e autosave
        '.prproj-backup': 'Backup de Projeto',
        '.prproj~': 'Backup Temporário',

        # Arquivos de configuração
        '.prsl': 'Preset de Layout do Premiere',
        '.prm': 'Módulo do Premiere',
        '.prmp': 'Preset de Marcador',

        # Arquivos de metadados
        '.xmp': 'Metadados XMP',
        '.xmpses': 'Sessão XMP',

        # Arquivos de legenda/closed caption
        '.scc': 'Scenarist Closed Caption',
        '.mcc': 'MacCaption File',
        '.srt': 'SubRip Subtitle',
        '.vtt': 'WebVTT Subtitle',
        '.xml': 'XML (pode conter dados do Premiere)',
    }

def is_premiere_related_folder(folder_name):
    """Verifica se a pasta está relacionada ao Premiere Pro"""
    folder_lower = folder_name.lower()
    premiere_keywords = [
        'premiere',
        'adobe premiere',
        'premiere pro',
        'ppro',
        'media cache files',
        'adobe',
        'video projects',
        'projetos premiere',
        'projetos video',
    ]
    return any(keyword in folder_lower for keyword in premiere_keywords)

def find_premiere_files_deep(drives=None, progress_callback=None):
    """
    Busca profunda por TODOS os arquivos relacionados ao Premiere Pro

    Args:
        drives: Lista de drives para buscar (None = todos os drives)
        progress_callback: Função para reportar progresso

    Returns:
        Tupla (arquivos_encontrados, pastas_premiere, estatísticas)
    """
    if drives is None:
        drives = get_available_drives()

    extensions = get_premiere_extensions()
    found_files = []
    premiere_folders = []
    stats = {
        'total_dirs_scanned': 0,
        'total_files_scanned': 0,
        'errors': 0,
        'access_denied': 0
    }

    # Diretórios a ignorar para melhor performance
    ignore_dirs = {
        'Windows', 'WinSxS', '$Recycle.Bin', 'System Volume Information',
        'Recovery', 'PerfLogs', 'node_modules', '.git', '.svn', '__pycache__',
        'AppData\\Local\\Temp', 'Temp', 'tmp'
    }

    print(f"Drives detectados: {', '.join(drives)}")
    print(f"Buscando por {len(extensions)} tipos de arquivos")
    print("=" * 80)

    for drive in drives:
        print(f"\n{'='*80}")
        print(f"BUSCANDO NO DRIVE: {drive}")
        print(f"{'='*80}\n")

        try:
            for root, dirs, files in os.walk(drive, topdown=True):
                stats['total_dirs_scanned'] += 1

                # Filtrar diretórios a ignorar
                dirs[:] = [d for d in dirs if not any(ignore in d for ignore in ignore_dirs)
                          and not d.startswith('.') and not d.startswith('$')]

                # Verificar se é uma pasta do Premiere
                current_folder = os.path.basename(root)
                if is_premiere_related_folder(current_folder) or is_premiere_related_folder(root):
                    premiere_folders.append(root)

                # Mostrar progresso
                if stats['total_dirs_scanned'] % 100 == 0:
                    print(f"Escaneados: {stats['total_dirs_scanned']} diretórios, "
                          f"{stats['total_files_scanned']} arquivos, "
                          f"{len(found_files)} arquivos do Premiere encontrados | "
                          f"Atual: {root[:60]}...", end='\r')

                for file in files:
                    stats['total_files_scanned'] += 1
                    file_lower = file.lower()
                    file_ext = os.path.splitext(file_lower)[1]

                    # Verificar extensão ou nome relacionado ao Premiere
                    is_premiere_file = (
                        file_ext in extensions or
                        'premiere' in file_lower or
                        file.endswith('.prproj-backup') or
                        file.endswith('.prproj~')
                    )

                    if is_premiere_file:
                        file_path = os.path.join(root, file)
                        try:
                            stats_info = os.stat(file_path)
                            file_info = {
                                'name': file,
                                'path': file_path,
                                'type': extensions.get(file_ext, 'Arquivo relacionado ao Premiere'),
                                'size': stats_info.st_size,
                                'size_formatted': format_size(stats_info.st_size),
                                'modified': datetime.fromtimestamp(stats_info.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                                'created': datetime.fromtimestamp(stats_info.st_ctime).strftime('%Y-%m-%d %H:%M:%S'),
                                'extension': file_ext,
                                'drive': drive
                            }
                            found_files.append(file_info)

                            # Mostrar quando encontrar um projeto
                            if file_ext == '.prproj':
                                print(f"\n✓ PROJETO ENCONTRADO: {file_path}")

                        except (PermissionError, OSError) as e:
                            stats['errors'] += 1
                            continue

        except PermissionError:
            stats['access_denied'] += 1
            print(f"\n⚠ Acesso negado ao drive: {drive}")
            continue
        except Exception as e:
            stats['errors'] += 1
            print(f"\n⚠ Erro ao escanear {drive}: {e}")
            continue

    print("\n" + "=" * 80)
    return found_files, premiere_folders, stats

def export_detailed_report(files, folders, stats, output_dir='premiere_scan_results'):
    """Exporta um relatório detalhado em múltiplos formatos"""

    # Criar diretório de saída
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # 1. Relatório em texto
    txt_file = os.path.join(output_dir, f'premiere_report_{timestamp}.txt')
    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write("=" * 100 + "\n")
        f.write("RELATÓRIO COMPLETO DE ARQUIVOS DO ADOBE PREMIERE PRO\n")
        f.write(f"Gerado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 100 + "\n\n")

        # Estatísticas
        f.write("ESTATÍSTICAS DA BUSCA\n")
        f.write("-" * 100 + "\n")
        f.write(f"Total de diretórios escaneados: {stats['total_dirs_scanned']:,}\n")
        f.write(f"Total de arquivos escaneados: {stats['total_files_scanned']:,}\n")
        f.write(f"Arquivos do Premiere encontrados: {len(files):,}\n")
        f.write(f"Pastas relacionadas ao Premiere: {len(folders):,}\n")
        f.write(f"Erros durante a busca: {stats['errors']}\n")
        f.write(f"Acessos negados: {stats['access_denied']}\n\n")

        # Agrupar por tipo
        by_type = {}
        total_size = 0
        for file in files:
            file_type = file['type']
            if file_type not in by_type:
                by_type[file_type] = []
            by_type[file_type].append(file)
            total_size += file['size']

        f.write(f"Tamanho total dos arquivos: {format_size(total_size)}\n\n")

        # Projetos do Premiere
        projects = [f for f in files if f['extension'] == '.prproj']
        if projects:
            f.write("\n" + "=" * 100 + "\n")
            f.write(f"PROJETOS DO PREMIERE PRO ({len(projects)} encontrado(s))\n")
            f.write("=" * 100 + "\n\n")

            for proj in sorted(projects, key=lambda x: x['modified'], reverse=True):
                f.write(f"Nome: {proj['name']}\n")
                f.write(f"Caminho: {proj['path']}\n")
                f.write(f"Drive: {proj['drive']}\n")
                f.write(f"Tamanho: {proj['size_formatted']}\n")
                f.write(f"Modificado: {proj['modified']}\n")
                f.write(f"Criado: {proj['created']}\n")
                f.write("-" * 100 + "\n\n")

        # Arquivos por tipo
        f.write("\n" + "=" * 100 + "\n")
        f.write("ARQUIVOS POR TIPO\n")
        f.write("=" * 100 + "\n\n")

        for file_type, file_list in sorted(by_type.items()):
            type_size = sum(f['size'] for f in file_list)
            f.write(f"\n{file_type.upper()} - {len(file_list)} arquivo(s) - {format_size(type_size)}\n")
            f.write("-" * 100 + "\n")

            for file in sorted(file_list, key=lambda x: x['size'], reverse=True)[:20]:  # Top 20 por tamanho
                f.write(f"  {file['name']} ({file['size_formatted']}) - {file['path']}\n")

            if len(file_list) > 20:
                f.write(f"  ... e mais {len(file_list) - 20} arquivos\n")
            f.write("\n")

        # Pastas do Premiere
        if folders:
            f.write("\n" + "=" * 100 + "\n")
            f.write(f"PASTAS RELACIONADAS AO PREMIERE ({len(folders)})\n")
            f.write("=" * 100 + "\n\n")
            for folder in sorted(set(folders)):
                f.write(f"  {folder}\n")

    # 2. Relatório em JSON
    json_file = os.path.join(output_dir, f'premiere_data_{timestamp}.json')
    json_data = {
        'scan_date': datetime.now().isoformat(),
        'statistics': stats,
        'files': files,
        'premiere_folders': list(set(folders)),
        'summary': {
            'total_files': len(files),
            'total_size': total_size,
            'total_size_formatted': format_size(total_size),
            'by_type': {k: len(v) for k, v in by_type.items()}
        }
    }

    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)

    # 3. Lista simples de projetos
    projects_file = os.path.join(output_dir, f'premiere_projects_list_{timestamp}.txt')
    with open(projects_file, 'w', encoding='utf-8') as f:
        f.write("LISTA DE PROJETOS DO PREMIERE PRO\n")
        f.write("=" * 100 + "\n\n")
        for proj in sorted(projects, key=lambda x: x['modified'], reverse=True):
            f.write(f"{proj['path']}\n")

    return txt_file, json_file, projects_file

def main():
    """Função principal"""
    print("=" * 100)
    print("BUSCA PROFUNDA DE ARQUIVOS DO ADOBE PREMIERE PRO")
    print("Busca em TODOS os drives disponíveis no sistema")
    print("=" * 100)
    print()

    # Detectar drives
    drives = get_available_drives()
    print(f"Drives detectados: {', '.join(drives)}")
    print()

    print("⚠ AVISO: Esta busca pode demorar bastante tempo dependendo da quantidade de arquivos.")
    print("         A busca irá escanear TODOS os drives disponíveis.")
    print()

    try:
        confirm = input("Deseja continuar com a busca profunda? (s/n): ").strip().lower()
        if confirm != 's':
            print("Busca cancelada.")
            return
    except KeyboardInterrupt:
        print("\n\nBusca cancelada pelo usuário.")
        return

    print("\nIniciando busca profunda...")
    print("Pressione Ctrl+C a qualquer momento para interromper.\n")

    start_time = datetime.now()

    try:
        files, folders, stats = find_premiere_files_deep(drives)
    except KeyboardInterrupt:
        print("\n\nBusca interrompida pelo usuário.")
        return

    end_time = datetime.now()
    duration = end_time - start_time

    # Mostrar resultados
    print("\n" + "=" * 100)
    print("RESULTADOS DA BUSCA")
    print("=" * 100)
    print(f"\nTempo de execução: {duration}")
    print(f"Diretórios escaneados: {stats['total_dirs_scanned']:,}")
    print(f"Arquivos escaneados: {stats['total_files_scanned']:,}")
    print(f"\nArquivos do Premiere encontrados: {len(files):,}")

    projects = [f for f in files if f['extension'] == '.prproj']
    print(f"Projetos (.prproj): {len(projects)}")

    if files:
        total_size = sum(f['size'] for f in files)
        print(f"Tamanho total: {format_size(total_size)}")

        # Mostrar resumo por drive
        by_drive = {}
        for f in files:
            drive = f['drive']
            if drive not in by_drive:
                by_drive[drive] = []
            by_drive[drive].append(f)

        print(f"\nDistribuição por drive:")
        for drive, file_list in sorted(by_drive.items()):
            print(f"  {drive}: {len(file_list)} arquivo(s)")

        # Perguntar se quer exportar
        print()
        export = input("Deseja exportar os resultados detalhados? (s/n): ").strip().lower()
        if export == 's':
            print("\nGerando relatórios...")
            txt_file, json_file, projects_file = export_detailed_report(files, folders, stats)
            print(f"\n✓ Relatórios gerados com sucesso:")
            print(f"  - Relatório completo: {txt_file}")
            print(f"  - Dados em JSON: {json_file}")
            print(f"  - Lista de projetos: {projects_file}")
            print(f"\nTodos os arquivos foram salvos na pasta: premiere_scan_results")
    else:
        print("\nNenhum arquivo do Premiere Pro foi encontrado.")

    print("\nBusca concluída!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nPrograma interrompido pelo usuário.")
    except Exception as e:
        print(f"\nErro inesperado: {e}")
        import traceback
        traceback.print_exc()
