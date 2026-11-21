"""SingMOS / SingMOS-Pro icin YAMA: engelli adrese (huggingface.co) gitmeden yukleme.

Sorun: resmi kod `s3prl.nn.S3PRLUpstream("wav2vec2_...")` cagirir; s3prl on-egitimli wav2vec2 dosyasini
huggingface.co'dan indirmeye calisir (bu ortamda engelli) ve ayrica s3prl.hub, torchaudio>=2.9 ile ice aktarilamaz.
Cozum: ince-ayarli SingMOS kontrol noktasi wav2vec2'nin TUM agirliklarini zaten icerir. Bu modul sahte bir
`s3prl.nn` kaydeder; mimariyi s3prl'in wav2vec2_model.py dosyasindan kurar, agirliklar kontrol noktasindan gelir.

Gerekenler: pip install --no-deps s3prl ; git clone --branch v1.1.2 https://github.com/South-Twilight/SingMOS
Agirliklar (github.com release): ckpt_s3prl/ft_wav2vec2_base_960_23steps.pt (380 MB),
                                 ckpt_v3/ft_wav2vec2_large_ll60k_mdf_p1_200epochs_all_192epochs.pth (1.27 GB)
"""
import sys, types, torch, torch.nn.functional as F

def _install_fake_s3prl_nn():
    from s3prl.upstream.wav2vec2.wav2vec2_model import Wav2Vec2Config, Wav2Vec2Model
    CFG = {
        "wav2vec2_base_960": (dict(quantize_targets=True, final_dim=256), False),
        "wav2vec2_large_ll60k": (dict(quantize_targets=True, final_dim=768, extractor_mode="layer_norm", layer_norm_first=True,
                                      conv_bias=True, encoder_layers=24, encoder_embed_dim=1024, encoder_ffn_embed_dim=4096,
                                      encoder_attention_heads=16), True),
    }
    class _Holder(torch.nn.Module):
        def __init__(self, model): super().__init__(); self.model = model
    class S3PRLUpstream(torch.nn.Module):
        def __init__(self, name):
            super().__init__()
            kw, self.wav_normalize = CFG[name]
            m = Wav2Vec2Model(Wav2Vec2Config(**kw)); m.feature_grad_mult = 0.0; m.encoder.layerdrop = 0.0
            self.upstream = _Holder(m)
        def forward(self, wav, wav_len):                      # wav [B, T]; tek, dolgusuz klip varsayilir
            if self.wav_normalize: wav = torch.stack([F.layer_norm(w, w.shape) for w in wav])
            x = self.upstream.model.extract_features(wav, None)["x"]
            return [x], None
    mod = types.ModuleType("s3prl.nn"); mod.S3PRLUpstream = S3PRLUpstream
    sys.modules["s3prl.nn"] = mod

def load(kind="pro", repo="/tmp/dinleme-a2/repolar/SingMOS", ckpt_dir="/tmp/dinleme-a2/modeller/singmos"):
    """kind: 'v1' veya 'pro'. Donus: predict(wav16k: np.ndarray float32) -> float (MOS tahmini)."""
    _install_fake_s3prl_nn()
    if repo not in sys.path: sys.path.insert(0, repo)
    if kind == "v1":
        from singmos.ssl_mos.singmos_v1 import MOS_Predictor
        model = MOS_Predictor(ssl_model_type="wav2vec2_base_960"); f = "ft_wav2vec2_base_960_23steps.pt"
    else:
        from singmos.ssl_mos.singmos_pro import MOS_Predictor
        model = MOS_Predictor(ssl_model_type="wav2vec2_large_ll60k", use_domain_id=True, domain_num=6)
        f = "ft_wav2vec2_large_ll60k_mdf_p1_200epochs_all_192epochs.pth"
    sd = torch.load(f"{ckpt_dir}/{f}", map_location="cpu", weights_only=True)
    model.load_state_dict(sd, strict=True); model.eval()
    def predict(wav16k):
        w = torch.from_numpy(wav16k)[None]
        with torch.no_grad():
            out = model(w, torch.tensor([w.shape[1]]))
        if isinstance(out, (tuple, list)): out = out[-1] if not torch.is_tensor(out[0]) else out[0]
        if isinstance(out, dict): out = next(v for v in out.values() if torch.is_tensor(v))
        return float(torch.as_tensor(out).flatten()[0])
    predict.model = model
    return predict
