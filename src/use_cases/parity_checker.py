"""Out-of-band parity auditor use case for hybrid cloud migration."""
from typing import Any, Dict

from src.ports.trade_repository import TradeRepository


class ParityCheckerUseCase:
    """Out-of-band parity auditor comparing on-premises and cloud repositories.

    Evaluates count drift, notional volume discrepancy, and ID delta without
    interfering with low-latency trading path.
    """

    def __init__(
        self,
        legacy_repo: TradeRepository,
        cloud_repo: TradeRepository,
    ) -> None:
        """Initialize with legacy and cloud repository ports.

        Args:
            legacy_repo: On-premise legacy TradeRepository.
            cloud_repo: Target cloud TradeRepository.
        """
        self._legacy_repo = legacy_repo
        self._cloud_repo = cloud_repo

    def execute(self) -> Dict[str, Any]:
        """Perform parity verification between legacy and cloud repositories.

        Calculates legacy_count, cloud_count, drift_count = abs(legacy_count - cloud_count),
        and volume_difference.

        Returns:
            Dict[str, Any]: Parity assessment dictionary with schema:
                {
                    "legacy_count": int,
                    "cloud_count": int,
                    "drift": int,
                    "status": "IN_PARITY" | "DRIFT_DETECTED",
                    "legacy_volume": float,
                    "cloud_volume": float,
                    "volume_difference": float,
                }
        """
        legacy_cnt = self._legacy_repo.count()
        cloud_cnt = self._cloud_repo.count()
        drift_cnt = abs(legacy_cnt - cloud_cnt)

        legacy_vol = self._legacy_repo.total_volume()
        cloud_vol = self._cloud_repo.total_volume()
        vol_diff = round(abs(legacy_vol - cloud_vol), 4)

        status = "IN_PARITY" if drift_cnt == 0 and vol_diff == 0.0 else "DRIFT_DETECTED"

        return {
            "legacy_count": legacy_cnt,
            "cloud_count": cloud_cnt,
            "drift": drift_cnt,
            "status": status,
            "legacy_volume": round(legacy_vol, 2),
            "cloud_volume": round(cloud_vol, 2),
            "volume_difference": vol_diff,
        }

    def get_missing_cloud_ids(self) -> set[str]:
        """Identify trade IDs present in legacy but missing in cloud.

        Returns:
            set[str]: Set of trade IDs requiring catch-up / replay.
        """
        legacy_ids = self._legacy_repo.get_all_ids()
        cloud_ids = self._cloud_repo.get_all_ids()
        return legacy_ids - cloud_ids
