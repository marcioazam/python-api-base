"""
Sustainability API router.

Provides REST endpoints for energy metrics, carbon emissions,
and sustainability reporting.
"""

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.infrastructure.sustainability.config import (
    SustainabilitySettings,
    get_sustainability_settings,
)
from src.infrastructure.sustainability.service import SustainabilityService

router = APIRouter(prefix="/sustainability", tags=["sustainability"])


class EnergyMetricResponse(BaseModel):
    """Energy metric response model."""

    namespace: str
    pod: str
    container: str
    energy_joules: str
    energy_kwh: str
    timestamp: str
    source: str


class CarbonMetricResponse(BaseModel):
    """Carbon metric response model."""

    namespace: str
    pod: str
    container: str
    energy_kwh: str
    emissions_gco2: str
    timestamp: str
    confidence_lower: str
    confidence_upper: str
    carbon_intensity_region: str
    carbon_intensity_gco2_per_kwh: str


class EmissionsResponse(BaseModel):
    """Emissions aggregation response model."""

    emissions_by_namespace: dict[str, str]
    total_emissions_gco2: str
    timestamp: str


class ReportResponse(BaseModel):
    """Sustainability report response model."""

    namespace: str
    period_start: str
    period_end: str
    total_energy_kwh: str
    total_emissions_gco2: str
    total_cost: str
    currency: str
    baseline_emissions_gco2: str | None
    target_emissions_gco2: str | None
    progress_percentage: str | None
    reduction_percentage: str | None


class CostResponse(BaseModel):
    """Energy cost response model."""

    energy_kwh: str
    price_per_kwh: str
    total_cost: str
    currency: str


def get_service(
    settings: Annotated[SustainabilitySettings, Depends(get_sustainability_settings)],
) -> SustainabilityService:
    """Dependency for sustainability service."""
    return SustainabilityService(settings)


@router.get("/metrics", response_model=list[EnergyMetricResponse])
async def get_energy_metrics(
    namespace: Annotated[str | None, Query(description="Filter by namespace")] = None,
    service: SustainabilityService = Depends(get_service),
) -> list[EnergyMetricResponse]:
    """
    Get energy consumption metrics from Kepler.

    Property 10: API Response Structure
    Response contains energy_kwh and required fields.
    """
    try:
        metrics = await service.get_energy_metrics(namespace)
        return [
            EnergyMetricResponse(
                namespace=m.namespace,
                pod=m.pod,
                container=m.container,
                energy_joules=str(m.energy_joules),
                energy_kwh=str(m.energy_kwh),
                timestamp=m.timestamp.isoformat(),
                source=m.source,
            )
            for m in metrics
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to fetch metrics: {e}",
        )


@router.get("/emissions", response_model=list[CarbonMetricResponse])
async def get_carbon_emissions(
    namespace: Annotated[str | None, Query(description="Filter by namespace")] = None,
    region: Annotated[
        str | None, Query(description="Region for carbon intensity")
    ] = None,
    service: SustainabilityService = Depends(get_service),
) -> list[CarbonMetricResponse]:
    """
    Get carbon emission metrics.

    Property 10: API Response Structure
    Response contains emissions_gco2 and confidence interval fields.
    """
    try:
        metrics = await service.get_carbon_metrics(namespace, region)
        return [
            CarbonMetricResponse(
                namespace=m.namespace,
                pod=m.pod,
                container=m.container,
                energy_kwh=str(m.energy_kwh),
                emissions_gco2=str(m.emissions_gco2),
                timestamp=m.timestamp.isoformat(),
                confidence_lower=str(m.confidence_lower),
                confidence_upper=str(m.confidence_upper),
                carbon_intensity_region=m.carbon_intensity.region,
                carbon_intensity_gco2_per_kwh=str(
                    m.carbon_intensity.intensity_gco2_per_kwh
                ),
            )
            for m in metrics
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to calculate emissions: {e}",
        )


@router.get("/emissions/aggregated", response_model=EmissionsResponse)
async def get_aggregated_emissions(
    namespace: Annotated[str | None, Query(description="Filter by namespace")] = None,
    service: SustainabilityService = Depends(get_service),
) -> EmissionsResponse:
    """Get aggregated emissions by namespace."""
    try:
        emissions = await service.get_emissions_by_namespace(namespace)
        total = sum(emissions.values())
        return EmissionsResponse(
            emissions_by_namespace={k: str(v) for k, v in emissions.items()},
            total_emissions_gco2=str(total),
            timestamp=datetime.now().isoformat(),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to aggregate emissions: {e}",
        )


@router.get("/reports/{namespace}", response_model=ReportResponse)
async def get_sustainability_report(
    namespace: str,
    period_start: Annotated[datetime, Query(description="Report period start")],
    period_end: Annotated[datetime, Query(description="Report period end")],
    baseline_emissions: Annotated[
        Decimal | None, Query(description="Baseline emissions for comparison")
    ] = None,
    target_emissions: Annotated[
        Decimal | None, Query(description="Target emissions goal")
    ] = None,
    service: SustainabilityService = Depends(get_service),
) -> ReportResponse:
    """Generate sustainability report for a namespace."""
    try:
        report = await service.generate_report(
            namespace=namespace,
            period_start=period_start,
            period_end=period_end,
            baseline_emissions=baseline_emissions,
            target_emissions=target_emissions,
        )
        return ReportResponse(
            namespace=report.namespace,
            period_start=report.period_start.isoformat(),
            period_end=report.period_end.isoformat(),
            total_energy_kwh=str(report.total_energy_kwh),
            total_emissions_gco2=str(report.total_emissions_gco2),
            total_cost=str(report.total_cost),
            currency=report.currency,
            baseline_emissions_gco2=(
                str(report.baseline_emissions_gco2)
                if report.baseline_emissions_gco2
                else None
            ),
            target_emissions_gco2=(
                str(report.target_emissions_gco2)
                if report.target_emissions_gco2
                else None
            ),
            progress_percentage=(
                str(report.progress_percentage)
                if report.progress_percentage
                else None
            ),
            reduction_percentage=(
                str(report.reduction_percentage)
                if report.reduction_percentage
                else None
            ),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to generate report: {e}",
        )


@router.get("/costs", response_model=CostResponse)
async def get_energy_costs(
    namespace: Annotated[str | None, Query(description="Filter by namespace")] = None,
    service: SustainabilityService = Depends(get_service),
) -> CostResponse:
    """Get energy cost calculations."""
    try:
        cost = await service.calculate_energy_cost(namespace)
        return CostResponse(
            energy_kwh=str(cost.energy_kwh),
            price_per_kwh=str(cost.price_per_kwh),
            total_cost=str(cost.total_cost),
            currency=cost.currency,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to calculate costs: {e}",
        )


@router.get("/export/csv")
async def export_metrics_csv(
    namespace: Annotated[str | None, Query(description="Filter by namespace")] = None,
    service: SustainabilityService = Depends(get_service),
) -> str:
    """Export carbon metrics as CSV."""
    try:
        metrics = await service.get_carbon_metrics(namespace)
        return service.export_metrics_csv(metrics)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to export metrics: {e}",
        )


@router.get("/export/json")
async def export_metrics_json(
    namespace: Annotated[str | None, Query(description="Filter by namespace")] = None,
    service: SustainabilityService = Depends(get_service),
) -> str:
    """Export carbon metrics as JSON."""
    try:
        metrics = await service.get_carbon_metrics(namespace)
        return service.export_metrics_json(metrics)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to export metrics: {e}",
        )
