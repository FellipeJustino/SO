# 💾 Benchmark de Gravação em File Systems

Trabalho de Sistemas Operacionais que mede o tempo de cópia de arquivos em 6 sistemas de arquivos diferentes, usando uma mesma partição NVMe reformatada a cada rodada.

Consultar Relatorio.html para visualização ampliada

## 🎯 O que foi testado

Dois cenários de cópia para cada file system:

- **Grande:** 5 arquivos `.zip` de 1 GB cada
- **Pequeno:** 1.000 arquivos `.txt` de ~1 KB cada

Cada arquivo foi copiado 10 vezes, cronometrando `cp` + `sync -f` em microssegundos.

## 📋 File systems

| File system | Cluster | Comando de criação |
|---|---|---|
| FAT32 (max) | 4 KB | `mkfs.fat -F 32 -S 512 -s 8` |
| FAT32 (min) | 512 B | `mkfs.fat -F 32 -S 512 -s 1` |
| NTFS | 512 B | `mkfs.ntfs -Q -c 512` |
| ext2 | 1024 B | `mkfs.ext2 -b 1024` |
| ext4 | 1024 B | `mkfs.ext4 -b 1024` |
| XFS | 512 B | `mkfs.xfs -f -b size=512 -m crc=0` |

## 📊 Resultados

| File system | Cluster | Grande (5 × 1 GB) | Pequeno (1000 × ~1 KB) |
|---|---|---|---|
| ext4 | 1024 B | 2,55 s | 8,86 ms |
| XFS | 512 B | 2,61 s | 7,79 ms |
| ext2 | 1024 B | 3,02 s | 5,50 ms |
| FAT32 (min) | 512 B | 4,11 s | 112,15 ms |
| FAT32 (max) | 4 KB | 6,27 s | 108,76 ms |
| NTFS | 512 B | 9,53 s | 4,31 ms |

## 🏆 Ranking

- **🥇 Grande:** ext4 > XFS > ext2 > FAT32 min > FAT32 max > NTFS
- **🥇 Pequeno:** NTFS > ext2 > XFS > ext4 > FAT32 max > FAT32 min
- **🏅 Melhor combinado:** ext2 (desempate por índice normalizado entre ext2, XFS e ext4)

## 📁 Estrutura do projeto

```
SO/
├── benchmark_cluster.sh               # Script de benchmark
├── gerar_relatorio.py                 # Gerador do relatório HTML
├── relatorio.html                     # Relatório visual (atalho)
└── Média_Tempo/                       # Resultados por rodada
    ├── relatorio.html                 # Relatório completo
    ├── ext2_cluster_min/
    ├── ext4_cluster_min/
    ├── fat32_cluster_max/
    ├── fat32_cluster_min/
    ├── ntfs_cluster_min/
    └── xfs_cluster_min/
        ├── tempos_brutos.csv
        ├── medias_por_arquivo.csv
        └── resumo_por_cenario.csv
```

## 👥 Contribuidores

- [github.com/FellipeJustino](https://github.com/FellipeJustino)
- [github.com/EduardoAugusto7](https://github.com/EduardoAugusto7)
