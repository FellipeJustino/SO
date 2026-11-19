# Trabalho de Sistemas Operacionais

Benchmark de desempenho de gravação em diferentes sistemas de arquivos, comparando o tempo de cópia de arquivos grandes e pequenos para uma mesma partição formatada com diferentes file systems e tamanhos de cluster.

## Objetivo

Medir e comparar o tempo médio de cópia por arquivo em dois cenários:

- **Cenário 1 (grande):** 5 arquivos `.zip` de 1 GB cada
- **Cenário 2 (pequeno):** 1.000 arquivos `.txt` de ~1 KB cada

Cada arquivo é copiado 10 vezes (repetições) para a partição de teste, usando `cp` seguido de `sync -f` para garantir a escrita em disco. O tempo é cronometrado em microssegundos com `date +%s%N`.

## Partição utilizada

- **Dispositivo:** `/dev/nvme0n1p6`
- **Ferramenta de particionamento:** GParted
- A partição foi formatada e remontada para cada sistema de arquivos testado, uma rodada por vez.

## Sistemas de arquivos testados

| Rodada | File system | Cluster | Comando de criação |
|---|---|---|---|
| fat32_cluster_max | FAT32 | 4 KB | `sudo mkfs.fat -F 32 -S 512 -s 8 /dev/nvme0n1p6` |
| fat32_cluster_min | FAT32 | 512 B | `sudo mkfs.fat -F 32 -S 512 -s 1 /dev/nvme0n1p6` |
| ntfs_cluster_min | NTFS | 512 B | `sudo mkfs.ntfs -Q -c 512 /dev/nvme0n1p6` |
| ext2_cluster_min | ext2 | 1024 B | `sudo mkfs.ext2 -b 1024 /dev/nvme0n1p6` |
| ext4_cluster_min | ext4 | 1024 B | `sudo mkfs.ext4 -b 1024 /dev/nvme0n1p6` |
| xfs_cluster_min | XFS | 512 B | `sudo mkfs.xfs -f -b size=512 -m crc=0 /dev/nvme0n1p6` |

### Comandos de consulta de cluster

| File system | Comando |
|---|---|
| FAT32 | `sudo fsck.fat -vn /dev/nvme0n1p6` |
| NTFS | `sudo ntfsinfo -m /dev/nvme0n1p6` |
| ext2 / ext4 | `sudo dumpe2fs -h /dev/nvme0n1p6` |
| XFS | `sudo xfs_info /dev/nvme0n1p6` |

### Observações

- O XFS com CRC ativo (padrão) exige bloco mínimo de 1024 bytes. Para usar 512 bytes, o CRC foi desativado com `-m crc=0`.
- O ext2/ext4 com bloco de 1024 bytes monta com diretório raiz pertencente ao root; foi necessário `sudo chown` no ponto de montagem antes de rodar o benchmark.
- O NTFS no Linux utiliza o driver ntfs3 do kernel para montagem com leitura e escrita.

## Metodologia

### Script de benchmark (`benchmark_cluster.sh`)

O script recebe três argumentos: o ponto de montagem da partição, o identificador do participante e um nome descritivo da rodada.

```
bash benchmark_cluster.sh <ponto_montagem> <participante> <descricao_run>
```

Exemplo:
```
bash benchmark_cluster.sh "$(findmnt -rno TARGET /dev/nvme0n1p6)" A fat32_cluster_max
```

**Fluxo de execução:**

1. Verifica se a partição está montada e acessível para escrita
2. Para cada repetição (1 a 10):
   - Cria uma pasta temporária na partição (`teste_bench_<participante>`)
   - Copia cada arquivo do cenário 1 (grande) e cenário 2 (pequeno) para a partição
   - Cada cópia é feita com `cp` seguido de `sync -f` no arquivo copiado
   - O tempo entre o `cp` e o `sync` é cronometrado com `date +%s%N` (precisão de nanossegundos, convertido para microssegundos)
   - Após cada cópia, verifica se o tamanho do arquivo copiado corresponde ao original
   - Em caso de falha em qualquer etapa (cópia, sync ou verificação de tamanho), o teste é interrompido
   - Ao fim de cada repetição, a pasta temporária é removida
3. Gera três arquivos CSV com os resultados

**Verificações de integridade:**

- `cp` e `sync` são verificados individualmente; falha em qualquer um interrompe o teste
- Comparação de tamanho (`stat -c %s`) entre origem e cópia
- `trap` para limpeza automática da pasta temporária em caso de erro ou interrupção

### Gerador de relatório (`gerar_relatorio.py`)

Script Python (stdlib, sem dependências externas) que lê os CSVs de todas as rodadas e gera `relatorio.html`.

```
python3 gerar_relatorio.py [pasta_Média_Tempo] [rodada_a_ignorar ...]
```

O relatório inclui:
- Resumo comparativo com tabelas e gráficos de barras
- Detalhamento por cenário com repetições individuais
- Comparação cruzada PA vs PB (duelos entre file systems)
- Ranking final com vencedores por cenário e melhor combinado

## Resultados

### Média por arquivo (10 repetições)

| File system | Cluster | Grande (5 × 1 GB) | Pequeno (1000 × ~1 KB) |
|---|---|---|---|
| ext4 cluster min | 1024 B | 2,55 s | 8,86 ms |
| XFS cluster min | 512 B | 2,61 s | 7,79 ms |
| ext2 cluster min | 1024 B | 3,02 s | 5,50 ms |
| FAT32 cluster min | 512 B | 4,11 s | 112,15 ms |
| FAT32 cluster max | 4 KB | 6,27 s | 108,76 ms |
| NTFS cluster min | 512 B | 9,53 s | 4,31 ms |

### Ranking

**Cenário 1 (grande):** ext4 > XFS > ext2 > FAT32 min > FAT32 max > NTFS

**Cenário 2 (pequeno):** NTFS > ext2 > XFS > ext4 > FAT32 max > FAT32 min

**Melhor combinado:** ext2 (desempate por índice normalizado entre ext2, XFS e ext4, todos com soma de posições = 5)

## Saída

Os resultados ficam em `Média_Tempo/<rodada>/`:

- `tempos_brutos.csv` — tempo de cada cópia individual (participante, cenário, repetição, arquivo, tempo em μs)
- `medias_por_arquivo.csv` — média das 10 repetições por arquivo (em ms)
- `resumo_por_cenario.csv` — média geral por cenário (em ms)
- `relatorio.html` — relatório visual com comparações, gráficos e ranking

## Contribuidores

- [github.com/FellipeJustino](https://github.com/FellipeJustino)
- [github.com/EduardoAugusto7](https://github.com/EduardoAugusto7)
