@REM ---------------------------------------------------------------------------
@REM |
@REM |  ActivateEnvironment.cmd
@REM |
@REM |  David Brownell (db@DavidBrownell.com)
@REM |      8/11/2015
@REM |
@REM ---------------------------------------------------------------------------
@REM |
@REM |  Copyright David Brownell 2015-18.
@REM |        
@REM |  Distributed under the Boost Software License, Version 1.0.
@REM |  (See accompanying file LICENSE_1_0.txt or copy at http://www.boost.org/LICENSE_1_0.txt)
@REM |
@REM ---------------------------------------------------------------------------
@echo off

pushd %~dp0

REM Get the python executable and the fullpath to the source repository tools.
REM This information is required to bootstrap the environment activation process.
if not exist "%~dp0Generated\Windows\EnvironmentBootstrap.data" (
    @echo.
    @echo ERROR: It appears that SetupEnvironment.cmd has not been run for this environment.
    @echo        Please run SetupEnvironment.cmd and run this script again.
    @echo. 
    @echo        [%~dp0Generated\Windows\EnvironmentBootstrap.data was not found]
    @echo.

    goto error_end
)

set _ACTIVATE_ENVIRONMENT_PREVIOUS_FUNDAMENTAL=%DEVELOPMENT_ENVIRONMENT_FUNDAMENTAL%

REM Parse the bootstrap info, extracting the python binary and fundamental root
for /f "tokens=1,2 delims==" %%a in (%~dp0Generated\Windows\EnvironmentBootstrap.data) do (
    if "%%a"=="python_binary" set PYTHON_BINARY=%%~fb
    if "%%a"=="fundamental_repo" set DEVELOPMENT_ENVIRONMENT_FUNDAMENTAL=%%~fb
    if "%%a"=="is_tool_repo" set _ACTIVATE_ENVIRONMENT_IS_TOOL_REPOSITORY=%%b
    if "%%a"=="is_configurable" set _ACTIVATE_ENVIRONMENT_IS_CONFIGURABLE_REPOSITORY=%%b
)

set PYTHONPATH=%DEVELOPMENT_ENVIRONMENT_FUNDAMENTAL%

@REM ----------------------------------------------------------------------
@REM |  List configurations if requested
if "%1" NEQ "ListConfigurations" goto :NotListConfiguration

REM Get the remaining args
set _ACTIVATE_ENVIRONMENT_WORKING_DIR=%~dp0
set _ACTIVATE_ENVIRONMENT_CLA=

shift

:GetRemainingArgs_ListConfigurations
if "%1" NEQ "" (
    set _ACTIVATE_ENVIRONMENT_CLA=%_ACTIVATE_ENVIRONMENT_CLA% %1
    shift
    goto :GetRemainingArgs_ListConfigurations
)

%PYTHON_BINARY% -m SourceRepositoryTools.Impl.ActivateEnvironment ListConfigurations %_ACTIVATE_ENVIRONMENT_WORKING_DIR% %_ACTIVATE_ENVIRONMENT_CLA%
goto end

:NotListConfiguration

@REM ----------------------------------------------------------------------
@REM |  Indicate if this is a tool repo if requested
if "%1" NEQ "IsToolRepository" goto :NotIsToolRepository

REM Get the remaining args
set _ACTIVATE_ENVIRONMENT_WORKING_DIR=%~dp0
set _ACTIVATE_ENVIRONMENT_CLA=

shift

:GetRemainingArgs_IsToolRepository
if "%1" NEQ "" (
    set _ACTIVATE_ENVIRONMENT_CLA=%_ACTIVATE_ENVIRONMENT_CLA% %1 
    shift 
    goto :GetRemainingArgs_IsToolRepository
)
    
%PYTHON_BINARY% -m SourceRepositoryTools.Impl.ActivateEnvironment IsToolRepository %_ACTIVATE_ENVIRONMENT_WORKING_DIR% %_ACTIVATE_ENVIRONMENT_CLA%
goto end

:NotIsToolRepository

@REM ----------------------------------------------------------------------
@REM |  Only allow one activated environment at a time (unless we are activating a tool repository).
if "%_ACTIVATE_ENVIRONMENT_IS_TOOL_REPOSITORY%" NEQ "1" if "%DEVELOPMENT_ENVIRONMENT_REPOSITORY%" NEQ "" if /i "%DEVELOPMENT_ENVIRONMENT_REPOSITORY%\" NEQ "%~dp0" (
    @echo.
    @echo ERROR: Only one environment can be activated at a time, and it appears as
    @echo        if one is already active. Please open a new console window and run
    @echo        this script again.
    @echo.
    @echo        [DEVELOPMENT_ENVIRONMENT_REPOSITORY is already defined as "%DEVELOPMENT_ENVIRONMENT_REPOSITORY%"]
    @echo.

    goto error_end
)

@REM ----------------------------------------------------------------------
@REM |  A tool repository can't be activated in isolation
if "%_ACTIVATE_ENVIRONMENT_IS_TOOL_REPOSITORY%"=="1" if "%DEVELOPMENT_ENVIRONMENT_REPOSITORY_ACTIVATED_FLAG%" NEQ "1" (
    @echo.
    @echo ERROR: A tool repository cannot be activated in isolation. Activate another repository before
    @echo        activating this one.
    @echo.
    
    goto reset_and_error_end
)

@REM ----------------------------------------------------------------------
@REM |  Prepare the args
if "%_ACTIVATE_ENVIRONMENT_IS_CONFIGURABLE_REPOSITORY%" NEQ "0" (
    if "%1" == "" (
        @echo.
        @echo ERROR: This environment is a configurable environment, which means that it
        @echo        can be activated in a variety of different configurations. Please 
        @echo        run this script again with a configuration name provided on the 
        @echo        command line.
        @echo.
        @echo        Available configuration names are:
        %PYTHON_BINARY% -m SourceRepositoryTools.Impl.ActivateEnvironment ListConfigurations %~dp0 indented
        @echo.

        goto reset_and_error_end
    )

    if "%DEVELOPMENT_ENVIRONMENT_REPOSITORY_CONFIGURATION%" NEQ "" (
        if "%DEVELOPMENT_ENVIRONMENT_REPOSITORY_CONFIGURATION%" NEQ "%1" (
            @echo.
            @echo ERROR: The environment was previously activated with a different configuration.
            @echo        Please open a new window and reactive the environment with the new 
            @echo        configuration.
            @echo.
            @echo        ["%DEVELOPMENT_ENVIRONMENT_REPOSITORY_CONFIGURATION%" != "%1"]
            @echo.

            goto reset_and_error_end
        )
    )

    set _ACTIVATE_ENVIRONMENT_CLA=%*

    goto cla_args_set
)

set _ACTIVATE_ENVIRONMENT_CLA=None %*

:cla_args_set

REM Create a temporary command file that contains the output of the setup scripts. This is necessary to
REM work around differences between the 64-bit command prompt and the 32-bit python version currently in
REM use.
call :create_temp_script_name

REM Generate...
%PYTHON_BINARY% -m SourceRepositoryTools.Impl.ActivateEnvironment Activate "%_ACTIVATE_ENVIRONMENT_TEMP_SCRIPT_NAME%" %~dp0 %_ACTIVATE_ENVIRONMENT_CLA%
set _ACTIVATE_ENVIRONMENT_SCRIPT_GENERATION_ERROR_LEVEL=%ERRORLEVEL%
if not exist "%_ACTIVATE_ENVIRONMENT_TEMP_SCRIPT_NAME%" goto :reset_and_error_end

REM Invoke...
call %_ACTIVATE_ENVIRONMENT_TEMP_SCRIPT_NAME%
set _ACTIVATE_ENVIRONMENT_SCRIPT_EXECUTION_ERROR_LEVEL=%ERRORLEVEL%

REM Process errors...
if %_ACTIVATE_ENVIRONMENT_SCRIPT_GENERATION_ERROR_LEVEL% NEQ 0 (
    @echo.
    @echo ERROR: Errors were encountered and the environment has not been successfully
    @echo        activated for development.
    @echo.
    @echo        [%DEVELOPMENT_ENVIRONMENT_FUNDAMENTAL%\SourceRepositoryTools\Impl\ActivateEnvironment.py failed]
    @echo.

    goto reset_and_error_end
)

if %_ACTIVATE_ENVIRONMENT_SCRIPT_EXECUTION_ERROR_LEVEL% NEQ 0 (
    @echo.
    @echo ERROR: Errors were encountered and the environment has not been successfully
    @echo        activated for development.
    @echo.
    @echo        [%_ACTIVATE_ENVIRONMENT_TEMP_SCRIPT_NAME% failed]
    @echo.

    goto reset_and_error_end
)

REM Cleanup...
del "%_ACTIVATE_ENVIRONMENT_TEMP_SCRIPT_NAME%"

@echo.
@echo.
@echo The environment has been activated and is ready for development.
@echo.
@echo.

set _ACTIVATE_ENVIRONMENT_ERROR_LEVEL=0
goto end

:reset_and_error_end
set DEVELOPMENT_ENVIRONMENT_FUNDAMENTAL=
goto error_end

:error_end
set _ACTIVATE_ENVIRONMENT_ERROR_LEVEL=-1
goto end

:end
set _ACTIVATE_ENVIRONMENT_SCRIPT_EXECUTION_ERROR_LEVEL=
set _ACTIVATE_ENVIRONMENT_SCRIPT_GENERATION_ERROR_LEVEL=
set _ACTIVATE_ENVIRONMENT_CLA=
set _ACTIVATE_ENVIRONMENT_WORKING_DIR=
set _ACTIVATE_ENVIRONMENT_TEMP_SCRIPT_NAME=
set _ACTIVATE_ENVIRONMENT_IS_CONFIGURABLE_REPOSITORY=
set _ACTIVATE_ENVIRONMENT_IS_TOOL_REPOSITORY=
set _ACTIVATE_ENVIRONMENT_PREVIOUS_FUNDAMENTAL=
set PYTHONPATH=

popd

exit /B %_ACTIVATE_ENVIRONMENT_ERROR_LEVEL%

@REM ---------------------------------------------------------------------------
:create_temp_script_name
setlocal EnableDelayedExpansion
set _filename=%~dp0\ActivateEnvironment-!RANDOM!-!Time:~6,5!.cmd
endlocal & set _ACTIVATE_ENVIRONMENT_TEMP_SCRIPT_NAME=%_filename%

if exist "%_ACTIVATE_ENVIRONMENT_TEMP_SCRIPT_NAME%" goto :create_temp_script_name
goto :EOF
@REM ---------------------------------------------------------------------------
