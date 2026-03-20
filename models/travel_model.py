import asyncio

from agents import (
    AggregatorAgent,
    ChatAgent,
    ItineraryAgent,
    TRAVEL_STYLE_AGENT_MAP,
)


class TravelModel:
    @staticmethod
    def _ensure_city_count(
        recommendations: list[dict],
        agent_results: list[dict],
        city_count: int,
    ) -> list[dict]:
        normalized = recommendations[:city_count]
        existing = {rec.get("city", "").strip().lower() for rec in normalized}

        if len(normalized) >= city_count:
            return normalized

        for agent in agent_results:
            for rec in agent.get("recommendations", []):
                city_name = str(rec.get("city", "")).strip()
                if not city_name:
                    continue
                key = city_name.lower()
                if key in existing:
                    continue
                normalized.append(
                    {
                        "city": city_name,
                        "reason": str(rec.get("reason", "Selected from specialist agent insights.")).strip(),
                    }
                )
                existing.add(key)
                if len(normalized) >= city_count:
                    return normalized

        return normalized

    async def run_plan(
        self,
        country: str,
        budget: str,
        duration: int,
        city_count: int,
        travel_styles: list[str],
        session_id: str,
    ) -> dict:
        agent_kwargs = dict(
            country=country,
            budget=budget,
            duration=duration,
            city_count=city_count,
            session_id=session_id,
        )

        selected = (
            {
                style: TRAVEL_STYLE_AGENT_MAP[style]
                for style in travel_styles
                if style in TRAVEL_STYLE_AGENT_MAP
            }
            if travel_styles
            else TRAVEL_STYLE_AGENT_MAP
        )

        style_results = await asyncio.gather(
            *(
                cls().run(**agent_kwargs, travel_styles=travel_styles)
                for style, cls in selected.items()
            )
        )

        agent_results = [
            {"agent_name": style, "recommendations": result["recommendations"]}
            for style, result in zip(selected, style_results)
        ]

        final_result = await AggregatorAgent().run(
            **agent_kwargs,
            travel_styles=travel_styles,
            agent_results=agent_results,
        )

        final_recommendations = self._ensure_city_count(
            recommendations=final_result["recommendations"],
            agent_results=agent_results,
            city_count=city_count,
        )

        itinerary_results = await asyncio.gather(
            *(
                ItineraryAgent().run(
                    **agent_kwargs,
                    city=rec["city"],
                    travel_styles=travel_styles,
                    reason=rec["reason"],
                )
                for rec in final_recommendations
            )
        )

        itineraries = [
            {"city": rec["city"], "days": itin["days"]}
            for rec, itin in zip(final_recommendations, itinerary_results)
        ]

        agent_details = {
            style: result["recommendations"]
            for style, result in zip(selected, style_results)
        }

        return {
            "country": country,
            "budget": budget,
            "duration": duration,
            "city_count": city_count,
            "travel_styles": travel_styles,
            "recommendations": final_recommendations,
            "itineraries": itineraries,
            "agent_details": agent_details,
        }

    async def run_chat(
        self,
        country: str,
        budget: str,
        duration: int,
        travel_styles: list[str],
        recommendations: list[dict],
        question: str,
        session_id: str,
    ) -> dict:
        return await ChatAgent().run(
            country=country,
            budget=budget,
            duration=duration,
            travel_styles=travel_styles,
            recommendations=recommendations,
            question=question,
            session_id=session_id,
        )
