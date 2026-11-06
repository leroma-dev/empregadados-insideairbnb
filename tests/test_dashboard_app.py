import dashboard.app as app_mod


def test_rodape_sem_atualizacao_diz_data_desconhecida(tmp_path, monkeypatch):
    monkeypatch.setattr(app_mod, "PASTA_PUBLICACAO", tmp_path)
    assert "data desconhecida" in app_mod.texto_rodape()


def test_rodape_com_data_valida(tmp_path, monkeypatch):
    (tmp_path / "atualizacao.json").write_text('{"gerado_em": "2026-11-06T02:00:00Z"}', encoding="utf-8")
    monkeypatch.setattr(app_mod, "PASTA_PUBLICACAO", tmp_path)
    assert "2026-11-06" in app_mod.texto_rodape()


def test_rodape_com_origem_invalida_nao_quebra(tmp_path, monkeypatch):
    monkeypatch.setattr(app_mod, "PASTA_PUBLICACAO", tmp_path)
    monkeypatch.setenv("DASHBOARD_ORIGEM", "planilha")
    assert "origem: indisponível" in app_mod.texto_rodape()
    assert app_mod.erro_origem() == app_mod.MSG_ORIGEM_INVALIDA


def test_rodape_com_json_invalido_nao_quebra(tmp_path, monkeypatch):
    (tmp_path / "atualizacao.json").write_text("{não é json", encoding="utf-8")
    monkeypatch.setattr(app_mod, "PASTA_PUBLICACAO", tmp_path)
    assert "data desconhecida" in app_mod.texto_rodape()
