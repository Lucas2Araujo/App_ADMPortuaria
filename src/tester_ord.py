import unittest
from datetime import datetime, timedelta
from ord_propriety import calcular_score
from cad import Navio, Carga

class TestCalculoScore(unittest.TestCase):
    def _criar_navio_com_cargas(self, imo_id, nome, cargas_data, horas_espera=0):
        """Método auxiliar (Factory) para instanciar navios e cargas reduzindo a duplicação (DRY)."""
        data_solicitacao = datetime.now() - timedelta(hours=horas_espera)
        navio = Navio(imo_id=imo_id, nome=nome, data_solicitacao=data_solicitacao)
        navio.cargas = [
            Carga(descricao=desc, categoria=cat, quantidade_toneladas=qtd, eh_perecivel=eh_per)
            for desc, cat, qtd, eh_per in cargas_data
        ]
        return navio

    def test_navio_carga_comum(self):
        """Teste para o Navio 1: Carga COMUM sem bônus de perecibilidade"""
        navio = self._criar_navio_com_cargas("A-001", "Navio da Virginia", [
            ("Minério de Ferro", "COMUM", 5000, False)
        ])
        
        score = calcular_score(navio)
        
        # Categoria COMUM = peso 0. Score de carga = 5000 * 0 = 0.
        # Bônus perecível = 0. Tempo de espera aprox 0.
        # Total esperado = 0
        self.assertAlmostEqual(score, 0, delta=1)

    def test_navio_carga_urgente(self):
        """Teste para o Navio 2: Carga Mista com URGENTE_PERECIVEL"""
        navio = self._criar_navio_com_cargas("A-002", "Barco do Vini JR", [
            ("Carnes Congeladas", "URGENTE_PERECIVEL", 200, True),
            ("Eletrônicos", "COMUM", 500, False)
        ])
        
        score = calcular_score(navio)
        
        # URGENTE_PERECIVEL (peso 3): 200 * 3 = 600
        # COMUM (peso 0): 500 * 0 = 0
        # Maior grau perecível = 3 -> bônus massivo = 3 * 10000 = 30000
        # Total esperado = 30600
        self.assertAlmostEqual(score, 30600, delta=1)

    def test_navio_carga_baixa_perecibilidade(self):
        """Teste para o Navio 3: Carga Mista com BAIXA_PERECIBILIDADE"""
        navio = self._criar_navio_com_cargas("A-003", "Colheita do Tigrinho", [
            ("Soja Úmida", "BAIXA_PERECIBILIDADE", 1000, True),
            ("Fertilizantes", "COMUM", 2000, False)
        ])
        
        score = calcular_score(navio)
        
        # BAIXA (peso 1): 1000 * 1 = 1000
        # COMUM (peso 0): 2000 * 0 = 0
        # Maior grau perecível = 1 -> bônus massivo = 1 * 10000 = 10000
        # Total esperado = 11000
        self.assertAlmostEqual(score, 11000, delta=1)

    def test_navio_carga_alta_perecibilidade(self):
        """Teste para o Navio 4: Múltiplas cargas ALTA_PERECIBILIDADE"""
        navio = self._criar_navio_com_cargas("A-004", "Faz o L", [
            ("Frutas Frescas", "ALTA_PERECIBILIDADE", 300, True),
            ("Laticínios", "ALTA_PERECIBILIDADE", 100, True)
        ])
        
        score = calcular_score(navio)
        
        # ALTA (peso 2): 400 * 2 = 800
        # Maior grau perecível = 2 -> bônus massivo = 2 * 10000 = 20000
        # Total esperado = 20800
        self.assertAlmostEqual(score, 20800, delta=1)

    def test_regra_anti_starvation_tempo_de_espera(self):
        """Teste da regra Anti-Starvation: Navio aguardando por 10 horas"""
        navio = self._criar_navio_com_cargas("A-005", "Esperançoso", [
            ("Aço", "COMUM", 1000, False)
        ], horas_espera=10)
        
        score = calcular_score(navio)
        
        # Cargas COMUM (peso 0): = 0
        # Tempo em horas = 10 * 1000 = 10000 de bônus anti-starvation
        # Total esperado = 10000 (com uma pequena margem de erro por conta de frações de segundos)
        self.assertAlmostEqual(score, 10000, delta=10)

    def test_comparacao_pior_vs_melhor_caso(self):
        """Teste de concorrência: Pior caso (pouca carga comum) vs Melhor caso (muita carga urgente)"""
        navio_pior = self._criar_navio_com_cargas("P-001", "Jangada do Zé", [
            ("Areia", "COMUM", 10, False)
        ])
        score_pior = calcular_score(navio_pior)
        
        navio_melhor = self._criar_navio_com_cargas("M-001", "Gigante dos Mares", [
            ("Vacinas", "URGENTE_PERECIVEL", 10000, True)
        ])
        score_melhor = calcular_score(navio_melhor)
        
        # O navio com carga urgente e pesada deve ter um score vastamente superior
        self.assertGreater(score_melhor, score_pior)
        
        self.assertAlmostEqual(score_pior, 0, delta=1)
        # Score_melhor = (10000 * 3) + 30000 (bônus máximo) = 60000
        self.assertAlmostEqual(score_melhor, 60000, delta=1)

if __name__ == '__main__':
    unittest.main()