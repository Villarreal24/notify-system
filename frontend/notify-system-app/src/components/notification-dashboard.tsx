"use client";

import { Badge, Box, Flex, Grid, Heading, Stack, Text } from "@chakra-ui/react";
import { useRouter } from "next/navigation";
import { useEffect, useOptimistic, useRef } from "react";

import { NotificationForm } from "@/components/notification-form";
import { NotificationLogList } from "@/components/notification-log-list";
import { SystemStats } from "@/components/system-stats";
import type { Category, NotificationLog } from "@/lib/api";
import type { OptimisticLogAction } from "@/lib/notification-types";

export function NotificationDashboard({
  categories,
  categoriesError,
  logs,
  logsError,
}: {
  categories: Category[];
  categoriesError?: string | null;
  logs: NotificationLog[];
  logsError?: string | null;
}) {
  const router = useRouter();
  const lastRefreshAt = useRef(0);
  const [optimisticLogs, addOptimisticLog] = useOptimistic(
    logs,
    (currentLogs, action: OptimisticLogAction) => {
      if (action.type === "rollback") {
        return currentLogs.filter((log) => log.id !== action.temporaryId);
      }

      if (action.type === "confirmMany") {
        const confirmedIds = new Set(action.logs.map((log) => log.id));
        return [
          ...action.logs,
          ...currentLogs.filter(
            (log) => log.id !== action.temporaryId && !confirmedIds.has(log.id),
          ),
        ];
      }

      return [
        action.log,
        ...currentLogs.filter((log) => log.id !== action.log.id),
      ];
    },
  );

  const confirmedLogs = optimisticLogs.filter(
    (log) => !log.id.startsWith("optimistic-"),
  );

  useEffect(() => {
    const refreshOnFocus = () => {
      if (document.visibilityState !== "visible") {
        return;
      }

      const now = Date.now();
      if (now - lastRefreshAt.current < 1_000) {
        return;
      }

      lastRefreshAt.current = now;
      router.refresh();
    };

    window.addEventListener("focus", refreshOnFocus);
    document.addEventListener("visibilitychange", refreshOnFocus);

    return () => {
      window.removeEventListener("focus", refreshOnFocus);
      document.removeEventListener("visibilitychange", refreshOnFocus);
    };
  }, [router]);

  return (
    <Box
      as="main"
      minH="100vh"
      overflowX="hidden"
      px={{ base: 5, md: 8 }}
      py={{ base: 5, md: 8 }}
      color="white"
      bg="radial-gradient(circle at 12% 18%, rgba(20, 184, 166, 0.42), transparent 34%), radial-gradient(circle at 86% 6%, rgba(56, 189, 248, 0.18), transparent 28%), linear-gradient(135deg, #020617 0%, #07111f 48%, #020617 100%)"
    >
      <Grid
        maxW="1240px"
        mx="auto"
        gap={8}
        templateColumns={{ base: "1fr", lg: "0.95fr 1.05fr" }}
      >
        <Box
          position="relative"
          minH={{ base: "auto", lg: "620px" }}
          overflow="hidden"
          rounded="42px"
          borderWidth="1px"
          borderColor="whiteAlpha.200"
          bg="linear-gradient(145deg, rgba(15, 23, 42, 0.78), rgba(2, 6, 23, 0.68))"
          boxShadow="0 28px 80px rgba(0, 0, 0, 0.35)"
          backdropFilter="blur(22px)"
          p={{ base: 6, md: 11 }}
        >
          <Box
            position="absolute"
            top="34px"
            right="34px"
            w="104px"
            h="104px"
            rounded="full"
            borderWidth="1px"
            borderColor="teal.200/35"
            boxShadow="inset 0 0 35px rgba(45, 212, 191, 0.12)"
          />
          <Text
            color="cyan.200"
            fontSize="xs"
            fontWeight="extrabold"
            letterSpacing="0.36em"
            textTransform="uppercase"
          >
            Notification System
          </Text>
          <Heading
            as="h1"
            maxW="680px"
            mt={{ base: 14, md: 20 }}
            fontSize={{ base: "3.5rem", md: "5rem", xl: "6rem" }}
            fontWeight="black"
            letterSpacing="-0.08em"
            lineHeight="0.86"
          >
            Route once, deliver everywhere.
          </Heading>
          <Text
            maxW="650px"
            mt={8}
            color="gray.300"
            fontSize="lg"
            lineHeight="1.8"
          >
            Send messages by category and let the backend find subscribed users,
            resolve their preferred channels, and record each delivery.
          </Text>
          <Box mt={13} position="relative" zIndex={1}>
            <SystemStats categories={categories} logs={confirmedLogs} />
          </Box>
        </Box>

        <Stack gap={6} align="stretch">
          {categoriesError ? (
            <Box
              rounded="2xl"
              borderWidth="1px"
              borderColor="red.300/35"
              bg="red.950/35"
              p={4}
              color="red.100"
              fontSize="sm"
              lineHeight="1.6"
            >
              {categoriesError}
            </Box>
          ) : null}
          <NotificationForm
            categories={categories}
            onOptimisticLogAction={addOptimisticLog}
          />
          <Box
            rounded="32px"
            borderWidth="1px"
            borderColor="whiteAlpha.200"
            bg="linear-gradient(145deg, rgba(15, 23, 42, 0.78), rgba(2, 6, 23, 0.68))"
            boxShadow="0 28px 80px rgba(0, 0, 0, 0.35)"
            backdropFilter="blur(22px)"
            p={7}
          >
            <Flex align="flex-end" justify="space-between" gap={4} mb={6}>
              <Box>
                <Text
                  color="cyan.200"
                  fontSize="xs"
                  fontWeight="extrabold"
                  letterSpacing="0.36em"
                  textTransform="uppercase"
                >
                  Log history
                </Text>
                <Heading as="h2" mt={2} fontSize="2xl">
                  Recent deliveries
                </Heading>
              </Box>
              <Badge
                minW="36px"
                h="36px"
                display="inline-flex"
                alignItems="center"
                justifyContent="center"
                rounded="full"
                colorPalette="teal"
                fontSize="sm"
              >
                {optimisticLogs.length}
              </Badge>
            </Flex>
            {logsError ? (
              <Box
                mb={5}
                rounded="2xl"
                borderWidth="1px"
                borderColor="red.300/35"
                bg="red.950/35"
                p={4}
                color="red.100"
                fontSize="sm"
                lineHeight="1.6"
              >
                {logsError}
              </Box>
            ) : null}
            <NotificationLogList logs={optimisticLogs} />
          </Box>
        </Stack>
      </Grid>
    </Box>
  );
}
